---
name: wp-eb-single-block-qa
description: >
  Complete pre-release QA for Essential Blocks "Single Block" WordPress plugins —
  the ~22 standalone one-block plugins WPDeveloper publishes on wordpress.org under
  the wpdevteam profile (Typing Text, Social Share Block, Table Of Contents Block,
  Image Comparison, Accordion Toggle, Countdown Block, and the rest). Installs a new
  release ZIP, tests it from a real user's perspective — registration, both inserters,
  every setting under General/Style/Advanced, editor vs frontend rendering, upgrade
  compatibility from the previous release, coexistence with the other single blocks,
  and a quick WordPress-specific security scan (sanitization/escaping, capability and
  nonce checks, REST/AJAX handling, an XSS spot-check) — compares it against the
  version currently live on wordpress.org, and writes a QA report. Use this skill whenever the user hands over a new Single Block ZIP to test,
  asks to QA/test/verify a Single Block release before it ships, wants to check a
  block for regressions against the wp.org version, or wants to confirm an upgrade
  path doesn't break existing content. Also trigger when the user mentions "single
  block QA", "test this block zip", "QA this release", or names one of the single
  block plugins by name alongside a version number or a request to test it. Distinct
  from wp-eb-test (which diffs EB suite pull requests against a git branch) and
  wp-eb-release-regression (which regression-tests the full EB suite, not a
  standalone single-block plugin) — use this skill specifically for a standalone
  single-block ZIP.
---

# Essential Blocks — Single Block QA

## What this is for

A tester hands you a new Single Block ZIP and says "test this." You install it, use
it the way a real user would, compare it against the version currently live on
wordpress.org, find what's broken, and write a report. Everything below serves that
and nothing else — don't add process for its own sake.

Work from the user's perspective, not a source-code audit. Never conclude something
works because the code looks right — click it, save it, reload it, look at the
frontend. Adapt to whatever the actual block has; skip controls that don't exist
rather than penalizing their absence. If you can't verify something, say
🔍 UNVERIFIED — never PASS on a guess.

## Three things about this fleet that a generic QA pass gets wrong

Read these once, at the start. They are the reason this skill exists rather than a
plain "test thoroughly" prompt, and each one produces a specific wrong result if
missed.

1. **The registered block name is not `<slug>/<slug>`.** 8 of the 19 blocks on the
   test site break that pattern — `typing-text/typing-text-block`,
   `social-share-block/social-share`, `countdown-block/countdown`,
   `price-table-block/pricing-table`, `testimonial-wp-block/testimonial`,
   `notice-block/notice`, `flipbox/flipbox-block`, `progress-bars/progress-bar-block`.
   Never assume the pattern — read the real name from `block.json` (or
   `eb_block_scan.py inspect`) and use that as truth throughout the run.

2. **Each plugin refuses to register if a specific Essential Blocks suite block is
   already registered**, and that guard target is a different string per plugin —
   sometimes the block's own name (a harmless no-op guard), sometimes a suite block
   it's genuinely trying to defer to. It has been wrong before:
   `social-share-block.php` carries a source comment describing the time its guard
   pointed at a name it never registered, so the guard silently deferred to the
   suite's block and stranded saved content. Extract the guard with
   `eb_block_scan.py inspect` and sanity-check it points at something plausibly
   related to this block, not a copy-paste from an unrelated one.

3. **All the single blocks reference the same shared script handle**
   (`essential-blocks-eb-animation`, plus a couple of others). WordPress's
   `wp_register_script()` silently ignores a duplicate handle — whichever plugin
   activates first wins, and every other plugin's "own" copy is never loaded. With
   every single block active at once, a frontend check can easily be exercising code
   from a plugin that isn't the one under test. This is exactly why P0 deactivates
   the others before testing, and why P10 re-checks it with everything active again.

## Inputs — infer, don't ask

| Input | Where it comes from |
|---|---|
| ZIP path | Given by the user, or the newest matching file in `~/Downloads/`. |
| Site | `blocksnew.local` — see `references/environment.md`. |
| Credentials | `~/EssentialBlocks-QA/defaults.json` → the `blocksnew` entry. Ask only if genuinely absent. |
| Baseline version | `python3 scripts/eb_block_scan.py baseline <slug>` — resolves the current wp.org release and the one before it. |

Only ask the user something none of the above can answer.

## The run

Old version installs first, on purpose: it turns into the fixture that both the
regression comparison and the upgrade test need, and it means the upgrade question
gets answered in the first hour instead of at the end of a long run, which is where
it would otherwise die.

| Phase | Work |
|---|---|
| **P0 — Identify & quarantine** | Run `eb_block_scan.py inspect <zip>` and `baseline <slug>`. Record block name, slug, version, guard target, and the exact wp.org baseline version in the report before anything else. **Stop here** if the version header didn't parse, the slug isn't a WPDeveloper plugin on wp.org, or no previous version exists to baseline against — say which piece failed rather than continuing on a guess. Deactivate the other single-block plugins on the site (note which ones, so they can be restored). |
| **P1 — Install baseline** | Install the previous wp.org release (WP Rollback, or upload the downloaded ZIP — see `references/environment.md`). Activate it. |
| **P2 — Build the fixture** | On the baseline version, insert the block, configure it realistically — a preset, a few structural toggles, real content, one responsive override — and save. Capture: the block's attributes (`wp.blocks.getBlockType(name).attributes` + `getBlockAttributes()`), the saved post content, and editor + frontend screenshots. **This one fixture is both the regression baseline and the upgrade-test subject.** |
| **P3 — Upgrade compatibility** | Upload the new ZIP over the old one and choose *Replace current with uploaded* (see `references/environment.md` for the exact click path). Reload the P2 fixture. Does it still validate? Are its attributes unchanged (or, if changed, does the changelog say why)? Does the frontend still match the P2 screenshot? This is the **Upgrade compatibility** verdict — it is about *existing* content surviving, nothing else. |
| **P4 — Fresh installation** | Delete the plugin entirely, then upload the new ZIP clean and activate. New post: registration, reachable through `/` and the `+` inserter, correct name/icon/category, insert it, does it render with sensible defaults. This is the **Fresh installation** verdict — registration and initial behavior, nothing about upgrades. |
| **P5 — Security scan** | Quick, targeted, on the clean P4 install — see "Security scan" below. Not a penetration test; the handful of checks that catch what actually goes wrong in this codebase. |
| **P6 — Editor validation + lifecycle** | No block-validation errors. Save, reload, still valid, settings persisted. Remove the block and re-add it. Then, on a saved block: deactivate the plugin, confirm WordPress shows it as unsupported (**expected — not a finding**), reactivate, confirm the content and settings came back exactly as saved. |
| **P7 — Every setting** | Walk General, Style and Advanced. Structural settings (presets, layout toggles, anything that changes what's on the page, not just how it looks) one at a time — change it, operate it through the real control, check editor and frontend both, this is where BLOCKERs hide. Cosmetic settings (color, typography, spacing, borders) in batches of ~10 per save/reload cycle, since one probe answers for the whole batch — check the frontend at the end of each batch, not later. Test every preset. Test enable/disable on every toggle. Cover all three responsive breakpoints for at least the controls that have them. |
| **P8 — Functionality & UX** | Every user-facing interaction, realistic content variations, edge states (empty, very long, special characters). Typos, misalignment, spacing, clipping, overflow, broken responsive behavior, dead controls, inconsistent labels. Skip anything with no user-facing impact. |
| **P9 — Regression** | Compare against the P2 baseline captures: registration, rendering, settings, presets, functionality, editor/frontend behavior, responsiveness. For anything different, check the changelog first — a documented change is ℹ️ INFO, not a regression. |
| **P10 — Coexistence** | Reactivate every plugin P0 deactivated. Confirm the block under test still registers and renders correctly with all of them active. Then build a page holding it alongside several other single blocks, save, reload, load the frontend: no block should show a validation error, and check the console for anything new. Re-check asset ownership here (see below) — this is the only phase where the shared-handle collision is actually reachable. |
| **P11 — Final check** | One more save/reload/frontend pass on a sensible configuration. Recheck the functionality that matters most. |

### Security scan (P5)

Grounded in the real code, not a generic checklist: these blocks render server-side through
a `render_callback`, and the shared style-handler writes attribute values straight into a
generated CSS file — so an unescaped color, URL or text attribute is a real path to stored
XSS here, not a hypothetical one. Custom REST routes and AJAX actions are rare on this
fleet — check for them, but expect "not applicable" more often than not, same as any other
control that doesn't exist.

Two halves, both reusing work the run is already doing rather than adding new machinery:

- **Static** — read the source already unzipped at P0. Look for: `$_GET`/`$_POST`/`$_REQUEST`
  used without a sanitizing function nearby; raw SQL string concatenation instead of
  `$wpdb->prepare()`; an attribute value echoed inside a `render_callback` or written into
  generated CSS without an `esc_html`/`esc_attr`/`esc_url` call; and, only where the plugin
  actually registers one, a `register_rest_route()` or `wp_ajax_*` handler missing a
  `permission_callback`, a `current_user_can()` check, or nonce verification.
- **Dynamic** — fold into P7's settings loop rather than running a separate pass: for one or
  two text/URL-type attributes, include one deliberately adversarial value (e.g. an unescaped
  `<script>` tag or a `"><img onerror=` payload) among the realistic content you're already
  trying, save it, and check the rendered output — editor and frontend both — comes back
  escaped, not raw.

**Verdict rules are the same ones the rest of the report already uses** — this section exists
to make that explicit, not to create a separate track. A confirmed, exploitable finding is a
BLOCKER, same as any other BLOCKER. If the same gap already exists in the P1 baseline's
source — check the retained baseline ZIP directly rather than reinstalling it live, that file
is already on disk from resolving the download URL — it's pre-existing, reported but not
ship-gating. Something that looks suspicious but can't actually be triggered is 🔍 UNVERIFIED;
never assert a vulnerability on suspicion alone. See `references/probes.md` for the specific
grep patterns and the payload/escaping check.

**Environment vs. release.** If a failure could plausibly be WordPress core, the
theme, a dependency, the browser, or the test environment rather than the block
itself, reproduce it on the P1 baseline before calling it a release regression.
Fails on both → pre-existing or environmental, note it, it doesn't gate this ship.
Fails only on the new ZIP → a real regression. Can't get it to reproduce either way →
🔍 UNVERIFIED. This matters more here than usual: the test site runs a WordPress
alpha build, and pinning an alpha-core quirk on the release is the easiest way for
this skill to be confidently wrong. Also worth checking directly: is the P1 baseline
itself healthy? A past Table Of Contents release (1.3.4–1.3.6) shipped with
registration silently broken — "no regression against baseline" means nothing if the
baseline was already broken. If that's the situation, judge against what the block is
supposed to do, not against a broken baseline.

Keep a plain running-notes file next to the report as you go — which phase you're on,
what's been tested, what you've found — so a compacted or interrupted session picks
up where it left off instead of re-testing from scratch or guessing at its own
coverage. Notes, not a tracking system: a few lines updated as you move through
phases is enough.

## Five more things that produce a confidently wrong result

- **Every DOM check has to go through the editor iframe.** WP 6.3+ renders block DOM
  inside `iframe[name="editor-canvas"]`. A `document.querySelector` against the top
  frame returns null, which reads as either a phantom BLOCKER or a silent false
  pass. See `references/probes.md` for the exact hop.
- **Operate the control — don't just dispatch to the attribute.** Setting
  `updateBlockAttributes()` directly proves the attribute round-trips through
  save/reload and proves nothing about whether the actual toggle, dropdown or color
  picker works. A disabled or mis-wired control passes every test if you only ever
  set the attribute programmatically. Click it, select it, type into it — then read
  the attribute back. Use direct dispatch only to cheaply restore state after a
  reload, never as the act of testing a control.
- **Save before navigating away.** Unsaved changes trigger a `beforeunload` dialog
  that Playwright handles unpredictably. Call `savePost()`, confirm it succeeded,
  then navigate.
- **Check who actually owns the loaded assets, from the frontend, after the last
  activation.** Every `/plugins/<x>/...` script or stylesheet URL on the page should
  have `<x>` equal to the slug under test. This is the direct check for trap #3 above
  — do it explicitly rather than assuming the right file loaded.
- **Check the generated CSS file right after saving, before loading the frontend.**
  The style handler regenerates it on both save *and* on any frontend visit, so
  checking after you've already loaded the frontend always shows a fresh file —
  telling you nothing about whether *save* triggered it correctly.

## Severity

- **BLOCKER** — can't register, insert, or render; a block-validation error; major
  frontend breakage; the upgrade path breaks existing content; a confirmed,
  exploitable security vulnerability.
- **HIGH** — a major functionality, settings, rendering, or regression problem.
- **MEDIUM** — a real but usable functional, responsive, or UI/UX problem.
- **LOW** — minor cosmetic or usability issue.

## Verdict

Two separate verdicts, because "does it work" means something different for a site
upgrading in place versus a fresh install, and a release can pass one while failing
the other:

- **Upgrade compatibility** — ✅ PASS / ❌ FAIL / 🔍 UNVERIFIED, from P3 against the
  P2 fixture: does existing saved content and its settings survive.
- **Fresh installation** — ✅ PASS / ❌ FAIL / 🔍 UNVERIFIED, from P4: registration,
  both inserters, correct default behavior on a clean install.

Neither stands in for the other. The overall release verdict can't be PASS while
either one is FAIL.

Three rules keep the verdict honest:

- **A Pass says how it was checked.** No evidence — including "the code looks
  correct" — means 🔍 UNVERIFIED, never Pass.
- **Any open BLOCKER means no overall PASS.** Not negotiable by a deadline. If the
  user pushes for a fast PASS, give them the honest state — what's checked, what
  isn't, what's still broken — and let them decide to ship anyway; don't make that
  call by softening the report.
- **A phase that didn't run gets named, with the reason.** Silence about a skipped
  phase is not the same as passing it.

Then use judgment — the numbers above are a floor, not a substitute for actually
thinking about whether this is shippable. Two calibrations specific to this fleet: a
`.eb-is-pro-message` upsell notice is never a finding, and a defect that also
reproduces on the P1 baseline is pre-existing — worth reporting, but it doesn't gate
this release.

## Report

Follow `references/report-template.md` for the exact shape — house style inherited
from `wp-eb-test`: caveman prose (short, no padding, but keep file paths, error text
and selectors in full), status markers always emoji **and** text so the report stays
greppable (`✅ PASS`, `❌ FAIL`, `⚠️ CONCERN`, `🔍 UNVERIFIED`, `🚫 BLOCKED`,
`ℹ️ INFO`).

Write to `/Users/siamzafar/Local Sites/eb/app/public/wp-content/plugins/eb-qa-reports/`,
screenshots alongside in `screenshots/`, named `NN-<symptom>.png`.

Include a compact Security section from P5 — one line per area checked (sanitization &
escaping, capability/nonce, REST/AJAX where applicable, the XSS spot-check, bundled-dependency
versions), each with a status marker and its evidence. Mark an area "not applicable" rather
than testing it when the plugin doesn't have that surface (no custom REST route, for
instance) — same rule as everywhere else in this skill. This is not a threat-model writeup;
that shape belongs to a dedicated security-review skill, not here.

Filename carries the block, version and outcome, so it's identifiable by `ls` alone:
`qa-report-<slug>-<version>-<result-or-primary-issue>-<YYYY-MM-DD>.md` — e.g.
`qa-report-typing-text-1.3.1-pass-2026-09-09.md`,
`qa-report-image-gallery-block-1.5.1-blocker-registration-guard-2026-09-09.md`.
Never overwrite an existing report; append `-2`, `-3` on a same-day collision. Never
number reports as "round N" — a re-test replaces the prior report's status, it
doesn't get appended as a new dated section.

After writing the local report, ask — never assume — whether to also publish it to
agent-notes. If yes, wrap long tables in `<details>` and grep the draft for "round"
before publishing.

## House rules

- Essential Blocks source repositories are read-only. Report bugs; never fix them,
  never commit to them.
- Never modify `wp-eb-test`, `wp-eb-release-regression`, or any other skill — borrow
  their conventions, don't touch their files.
- Restore whatever plugin activation state P0 changed once P10 has re-checked it.
- Ask before any FluentBoards write or agent-notes publish/overwrite.

## Anti-patterns

Each of these has produced a wrong result in practice, not a hypothetical one:

- Asserting `<slug>/<slug>` as the registered name instead of reading it from
  `block.json` — fires a phantom BLOCKER on 8 of 19 blocks.
- Trusting a frontend check without deactivating the other single blocks first — the
  evidence can belong to a different plugin entirely.
- Testing a control only via `updateBlockAttributes()` — proves nothing about
  whether the control itself works.
- Checking the generated CSS file after visiting the frontend — always looks fresh,
  proves nothing about whether *save* regenerated it.
- Calling something a regression because it fails on the new ZIP, without checking
  whether it also fails on the baseline — an environment issue isn't a release issue.
- Treating "shows as an unsupported block while the plugin is deactivated" as a
  finding — that's WordPress working as designed; the real question is whether it
  recovers on reactivation.
- Softening a BLOCKER into a lower severity, or marking PASS with unreported skipped
  phases, because the user is in a hurry.
