# wp-eb-single-block-qa

A Claude Code skill for pre-release QA of Essential Blocks "Single Block" WordPress
plugins — the ~22 standalone one-block plugins WPDeveloper publishes on
wordpress.org under the [wpdevteam profile](https://profiles.wordpress.org/wpdevteam/)
(Typing Text, Social Share Block, Table Of Contents Block, Image Comparison,
Accordion Toggle, and the rest).

Hand it a new release ZIP and it installs it, tests it the way a real user would —
registration, both inserters, every setting, editor vs. frontend rendering, upgrade
compatibility from the previous release, coexistence with the other single blocks, a
quick WordPress-specific security scan — compares it against whatever's currently
live on wordpress.org, and writes a report.

## What it knows that a generic "test this thoroughly" prompt doesn't

Three facts about this specific plugin fleet, found by inspecting the actual shipped
code rather than assuming convention:

1. The registered block name isn't reliably `<slug>/<slug>` — several blocks use a
   different internal name than their folder slug.
2. Each plugin has a registration guard that defers to a specific Essential Blocks
   suite block name, and that guard target has been wrong before (a copy-paste from
   an unrelated block), silently killing registration when the suite is active.
3. All the single blocks reference a shared script handle. WordPress keeps only the
   first plugin's registration of a duplicate handle — so with several single blocks
   active, a frontend check can end up exercising the wrong plugin's code.

See `SKILL.md` for how the run is structured around these.

## Setup on a new machine

Everything machine-specific — the test site, credentials, install/rollback click
paths, report location — lives in `references/environment.md` alone. To use this on
a different WordPress install:

1. Edit `references/environment.md` to point at your test site and report directory.
2. Set up a credentials source the skill can read (this repo assumes a local
   `defaults.json`; adapt to however you manage secrets — nothing is or should be
   committed to this repo).
3. Everything else — `SKILL.md`, `scripts/eb_block_scan.py`, `references/probes.md`,
   `references/report-template.md` — is portable as-is.

## Requirements

- Python 3.9+ for `scripts/eb_block_scan.py` (stdlib only, no dependencies).
- A browser-automation MCP tool (this skill is written against Playwright MCP).
- Network access to `api.wordpress.org` and `downloads.wordpress.org` to resolve
  release baselines.

## Files

- `SKILL.md` — the workflow, severity, verdict rules.
- `scripts/eb_block_scan.py` — deterministic ZIP inspection and wp.org baseline
  resolution. Run `python3 scripts/eb_block_scan.py --help`.
- `references/environment.md` — the machine-specific configuration.
- `references/probes.md` — browser-automation snippets, each documented with the
  specific false result it prevents.
- `references/report-template.md` — the report skeleton.
- `evals/evals.json` — test scenarios for this skill, built for skill-creator.

## Scope

Read-only against Essential Blocks source. This skill reports bugs; it never fixes
them or commits to plugin repositories.
