# Environment

The one machine-specific file in this skill. Everything else is portable; this is
not, and shouldn't need to be — a new machine gets a new copy of this file.

## Test site

**`blocksnew.local`** — `/Users/siamzafar/Local Sites/blocksnew/app/public`

Chosen deliberately: it carries all ~19 single blocks (so P10 coexistence testing
needs no extra setup) and does *not* have the Essential Blocks suite installed,
which means it can't collide with the suite on category, icon or shortcut
registration while you're testing a standalone block. It also has **WP Rollback**
and **core-rollback** installed, which is what makes swapping plugin versions in
place practical.

**Same site, both versions, always.** Never install the baseline on one site and the
new ZIP on another — a difference between two different WordPress builds, themes or
plugin sets is not evidence of a regression, it's noise.

**WordPress 7.1.1-alpha.** The site runs a beta/alpha core via `wordpress-beta-tester`.
Record this version in every report. If a failure looks like it could be a core
issue rather than the block, that's exactly the case the SKILL.md "Environment vs.
release" rule exists for — reproduce it against the P1 baseline before blaming the
release.

## Credentials

`~/EssentialBlocks-QA/defaults.json` — read the `blocksnew` entry:

```json
{
  "blocksnew": {
    "site_url": "http://blocksnew.local/",
    "wp_user": "<admin username>",
    "wp_pass": "<admin password>"
  }
}
```

If that entry doesn't exist yet, ask the user once for the admin login and offer to
save it there for next time — never hardcode credentials into this skill or into any
report; this repo may end up public.

## Installing a plugin version

No WP-CLI on this machine. Everything goes through wp-admin, driven by Playwright —
which is also the more accurate user-perspective test anyway.

**Fresh install (P1, P4):**
1. Plugins → Add New Plugin → Upload Plugin.
2. Choose the ZIP file, Install Now, Activate.

**Upgrade in place (P3) — the click path that's easy to miss:**
1. Plugins → Add New Plugin → Upload Plugin → choose the new ZIP → Install Now.
2. WordPress detects a plugin already exists at that slug and shows a **comparison
   screen**, not a plain success message. You must explicitly click
   **"Replace current with uploaded"** — it does not happen automatically, and if you
   stop at the comparison screen thinking the install is done, the old version is
   still active and every subsequent check is silently testing the wrong version.
3. Confirm the replacement. Re-check the version number in Plugins after this step —
   don't just trust that the click succeeded.

**Roll back to a specific wp.org release (P1 alternative to a manual download):**
Plugins → find the block → **WP Rollback** action → choose the exact version from
the dropdown → Rollback. Faster than downloading the ZIP from wp.org yourself when
you just need the previous release installed.

**Downloading a specific version manually**, when you need the file rather than an
in-place rollback (e.g. to keep a copy, or WP Rollback isn't listing it):
`eb_block_scan.py baseline <slug>` prints `previous_download_url` and
`latest_download_url` — both direct `https://downloads.wordpress.org/plugin/...zip`
links, fetchable with a plain download.

## Deleting a plugin (P4 fresh-install step)

Plugins → Deactivate → Delete. Any page holding a saved instance of the block will
show it as an unsupported block while the plugin is gone — expected WordPress
behavior, not a finding (see SKILL.md). It recovers once the plugin is reinstalled
and reactivated.

## Quarantine (P0) and restore (P10)

P0 needs the *current* list of active single-block plugins, not a hardcoded one —
new blocks get added to this site over time. Get it live:
- Plugins screen, or `browser_evaluate` against
  `wp.apiFetch({ path: '/wp/v2/plugins' })` filtered to `status: 'active'`.

Deactivate every single-block plugin except the one under test. Note exactly which
ones you turned off — P10 needs to reactivate precisely those, not "all of them",
in case one was already inactive before you started for an unrelated reason.

## Generated CSS

Each single block writes per-post CSS to
`wp-content/uploads/eb-style/eb-style-<postID>.min.css` on save. Useful as objective
evidence that a style setting actually took effect — see the SKILL.md note on
checking it *after save, before the frontend visit* (the frontend visit itself
regenerates the file, which would make the check pass regardless of whether save did
its job).

## Reports

`/Users/siamzafar/Local Sites/eb/app/public/wp-content/plugins/eb-qa-reports/` — a
plain markdown archive (not a real WordPress plugin — no PHP in it, just reports).
Screenshots go in a `screenshots/` subfolder there, named `NN-<symptom>.png`.

This is a different site (`eb.local`) from the test site (`blocksnew.local`) — that's
intentional and existing convention; the report archive lives alongside the rest of
the EB QA corpus regardless of which site produced the finding.
