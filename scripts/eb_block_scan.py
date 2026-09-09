#!/usr/bin/env python3
"""
eb_block_scan.py — deterministic extraction for Essential Blocks "Single Block" QA.

Handles the parts an LLM gets subtly wrong: WordPress-rule plugin-header parsing
(some headers indent `Version:` inside a docblock, which a naive `^ \* Version:`
regex misses and silently returns empty), wp.org version-history ordering, and
pulling the `is_registered()` guard argument out of the main PHP file.

Fails loudly rather than returning an empty result — an empty result that reads
as success is how a scanner lies. Every subcommand prints one JSON object to
stdout and exits non-zero on anything it could not determine.

Subcommands:
  inspect  <zip-path>        Block name, guard name, version (3-way), changelog
                              for this version, and the JS bundle files found.
  baseline <slug>            wp.org: latest version, all released versions in
                              order, the one immediately before a given version
                              (or before latest if none given), download links.

Usage:
  python3 eb_block_scan.py inspect ~/Downloads/typing-text.1.3.1.zip
  python3 eb_block_scan.py baseline typing-text
  python3 eb_block_scan.py baseline typing-text --before 1.3.1
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import urllib.request
import zipfile
from pathlib import Path


def fail(msg: str, **extra) -> None:
    """Print a JSON error object and exit non-zero. Never return an empty success shape."""
    out = {"error": msg}
    out.update(extra)
    print(json.dumps(out, indent=2))
    sys.exit(1)


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------

# WordPress's own header-parsing rule (see wp-admin/includes/plugin.php
# get_plugin_data): match "Version:" preceded by any run of space/tab/*/#/@ —
# covers a bare "// Version: 1.0" line AND "     * Version:     1.0" inside a
# /** ... */ docblock, which social-share-block.php uses and a plain
# ^\s*\*\s*Version: regex will not, because there are two extra leading spaces
# before the asterisk itself in that file.
HEADER_RE = {
    "Version": re.compile(r"^[ \t/*#@]*Version:\s*(.*)$", re.MULTILINE | re.IGNORECASE),
    "Plugin Name": re.compile(r"^[ \t/*#@]*Plugin Name:\s*(.*)$", re.MULTILINE | re.IGNORECASE),
    "Text Domain": re.compile(r"^[ \t/*#@]*Text Domain:\s*(.*)$", re.MULTILINE | re.IGNORECASE),
}

GUARD_RE = re.compile(
    r"is_registered\(\s*['\"]([a-z0-9_-]+/[a-z0-9_-]+)['\"]",
    re.IGNORECASE,
)
# The guard argument is sometimes a variable rather than an inline string literal
# (e.g. social-share-block.php: `$block_name = 'social-share-block/social-share';`
# ... `is_registered( $block_name )`). Match that call shape, then resolve the
# variable's most recent prior assignment to a string literal.
GUARD_VAR_RE = re.compile(r"is_registered\(\s*\$([A-Za-z_][A-Za-z0-9_]*)\s*\)")


def resolve_guard_name(php_src: str) -> str | None:
    m = GUARD_RE.search(php_src)
    if m:
        return m.group(1)
    m = GUARD_VAR_RE.search(php_src)
    if not m:
        return None
    var, call_pos = m.group(1), m.start()
    assign_re = re.compile(
        r"\$" + re.escape(var) + r"\s*=\s*['\"]([a-z0-9_-]+/[a-z0-9_-]+)['\"]",
        re.IGNORECASE,
    )
    # Last assignment before the is_registered() call wins — that's the value in scope there.
    last = None
    for am in assign_re.finditer(php_src, 0, call_pos):
        last = am.group(1)
    return last


def parse_header(php_head: str) -> dict:
    out = {}
    for key, rx in HEADER_RE.items():
        m = rx.search(php_head)
        out[key] = m.group(1).strip() if m else ""
    return out


def find_main_php(zf: zipfile.ZipFile, slug: str) -> str | None:
    """The main plugin file is <slug>/<slug>.php per wp.org convention. Fall back
    to any top-level .php file in the slug folder carrying a 'Plugin Name:' header,
    in case a block does not follow the convention exactly."""
    candidate = f"{slug}/{slug}.php"
    names = zf.namelist()
    if candidate in names:
        return candidate
    for n in names:
        if n.startswith(f"{slug}/") and n.count("/") == 1 and n.endswith(".php"):
            try:
                head = zf.read(n).decode("utf-8", errors="replace")[:4096]
            except Exception:
                continue
            if "Plugin Name:" in head:
                return n
    return None


def extract_changelog_entry(readme_text: str, version: str) -> str:
    """Pull the '= <version> - ...  =' section out of a wp.org readme.txt Changelog."""
    # Section headers look like "= 1.4.0 - 20/08/2026 =" — match the version loosely
    # (readme may or may not include the date on the same line).
    pattern = re.compile(
        r"^=\s*" + re.escape(version) + r"\b.*?=\s*\n(.*?)(?=^\s*=\s*\d|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(readme_text)
    return m.group(1).strip() if m else ""


def classify_bundles(zf: zipfile.ZipFile, slug: str) -> dict:
    """List every JS file under dist/ with its size, so the agent can tell an
    editor bundle from a controls/modules bundle by content, not by a filename
    assumption — only image-comparison ships dist/controls.js, everything else
    ships dist/modules.js, and a script that globs one name silently sees nothing
    on the rest of the fleet."""
    bundles = []
    for info in zf.infolist():
        if info.filename.startswith(f"{slug}/dist/") and info.filename.endswith(".js"):
            bundles.append({"path": info.filename, "bytes": info.file_size})
    bundles.sort(key=lambda b: -b["bytes"])
    return bundles


def cmd_inspect(args) -> None:
    zip_path = Path(args.zip_path).expanduser()
    if not zip_path.is_file():
        fail(f"zip not found: {zip_path}")

    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        fail(f"not a valid zip: {zip_path}")

    names = zf.namelist()
    if not names:
        fail("zip is empty")

    # Top-level folder = plugin slug, by wp.org convention.
    top = names[0].split("/")[0]
    slug = top

    main_php = find_main_php(zf, slug)
    if not main_php:
        fail(
            f"could not find a main plugin PHP file under '{slug}/' with a "
            "Plugin Name header — cannot resolve version or identity",
            slug=slug,
            top_level_entries=sorted({n.split("/")[0] for n in names})[:20],
        )

    php_src = zf.read(main_php).decode("utf-8", errors="replace")
    header = parse_header(php_src[:6000])
    version_header = header.get("Version", "")
    if not version_header:
        fail(
            f"Version header did not parse from {main_php} — refusing to guess. "
            "The plugin header format may have changed; check it by hand.",
            slug=slug,
            main_php=main_php,
        )

    guard_name = resolve_guard_name(php_src)

    block_json_name = None
    block_json_version = None
    block_json_path = f"{slug}/block.json"
    if block_json_path in names:
        try:
            bj = json.loads(zf.read(block_json_path).decode("utf-8", errors="replace"))
            block_json_name = bj.get("name")
            block_json_version = bj.get("version")
        except json.JSONDecodeError:
            pass  # not fatal — block.json version is a bonus cross-check, not the source of truth

    readme_path = f"{slug}/readme.txt"
    readme_version = None
    changelog_entry = ""
    if readme_path in names:
        readme_text = zf.read(readme_path).decode("utf-8", errors="replace")
        m = re.search(r"^Stable tag:\s*(.+)$", readme_text, re.MULTILINE | re.IGNORECASE)
        readme_version = m.group(1).strip() if m else None
        changelog_entry = extract_changelog_entry(readme_text, version_header)

    version_agreement = {
        "plugin_header": version_header,
        "block_json": block_json_version,
        "readme_stable_tag": readme_version,
        "agree": len(
            {v for v in (version_header, block_json_version, readme_version) if v}
        )
        <= 1,
    }

    result = {
        "slug": slug,
        "plugin_name": header.get("Plugin Name", ""),
        "text_domain": header.get("Text Domain", ""),
        "main_php": main_php,
        "version": version_header,
        "version_agreement": version_agreement,
        "block_json_name": block_json_name,
        "registration_guard": guard_name,
        "changelog_for_this_version": changelog_entry or None,
        "js_bundles": classify_bundles(zf, slug),
    }

    if not block_json_name:
        result["warning"] = f"no block.json name found at {block_json_path} — cannot verify registered block name"

    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# baseline
# ---------------------------------------------------------------------------

def version_key(v: str):
    """Sort key for dotted version strings; non-numeric parts (e.g. 'trunk') sort last."""
    parts = re.split(r"[.\-]", v)
    key = []
    for p in parts:
        if p.isdigit():
            key.append((0, int(p)))
        else:
            key.append((1, p))
    return key


def cmd_baseline(args) -> None:
    slug = args.slug
    url = (
        "https://api.wordpress.org/plugins/info/1.2/"
        f"?action=plugin_information&request%5Bslug%5D={slug}"
    )
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        fail(f"wp.org API request failed for slug '{slug}': {e}", slug=slug)

    if "error" in data or not data.get("slug"):
        fail(f"wp.org has no plugin at slug '{slug}'", slug=slug, response=data)

    author_profile = data.get("author_profile", "")
    if "profiles.wordpress.org/wpdevteam" not in author_profile:
        # Not fatal — just flagged, since the skill's baseline-of-record is specifically
        # the wpdevteam profile and a mismatch here means the slug may be wrong.
        author_flag = f"author_profile is '{author_profile}', not the wpdevteam profile"
    else:
        author_flag = None

    versions = dict(data.get("versions") or {})
    versions.pop("trunk", None)
    if not versions:
        fail(f"wp.org returned no version history for '{slug}'", slug=slug)

    ordered = sorted(versions.keys(), key=version_key)
    latest = data.get("version") or ordered[-1]

    reference = args.before or latest
    if reference not in ordered:
        fail(
            f"version '{reference}' not found in wp.org history for '{slug}'",
            slug=slug,
            known_versions=ordered,
        )
    idx = ordered.index(reference)
    previous = ordered[idx - 1] if idx > 0 else None
    if previous is None:
        fail(
            f"'{reference}' is the earliest released version on wp.org for '{slug}' — "
            "no previous version exists to use as a baseline",
            slug=slug,
            known_versions=ordered,
        )

    result = {
        "slug": slug,
        "name": data.get("name"),
        "author_profile": author_profile,
        "author_flag": author_flag,
        "latest_version": latest,
        "reference_version": reference,
        "previous_version": previous,
        "previous_download_url": f"https://downloads.wordpress.org/plugin/{slug}.{previous}.zip",
        "latest_download_url": f"https://downloads.wordpress.org/plugin/{slug}.{latest}.zip",
        "requires_wp": data.get("requires"),
        "tested_up_to": data.get("tested"),
        "last_updated": data.get("last_updated"),
        "all_versions_ordered": ordered,
    }
    print(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_inspect = sub.add_parser("inspect", help="Extract identity facts from a block ZIP")
    p_inspect.add_argument("zip_path")
    p_inspect.set_defaults(func=cmd_inspect)

    p_baseline = sub.add_parser("baseline", help="Resolve the wp.org release baseline for a slug")
    p_baseline.add_argument("slug")
    p_baseline.add_argument(
        "--before",
        default=None,
        help="Find the version immediately before this one (default: before the current latest)",
    )
    p_baseline.set_defaults(func=cmd_baseline)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
