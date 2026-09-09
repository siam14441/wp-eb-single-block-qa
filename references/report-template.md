<!--
QA REPORT TEMPLATE — wp-eb-single-block-qa skill

How to use this file:
- Copy this structure into a new report and fill in every {{placeholder}}.
- Write style: caveman. Short sentences, no fluff — "Block renders. No errors.
  Settings persist." NOT "The block renders correctly and settings appear to
  persist as expected." File paths, error text, selectors, version numbers: keep
  FULL, never trim these.
- Status markers are always emoji + text, e.g. "✅ PASS", "❌ FAIL", "⚠️ CONCERN",
  "🔍 UNVERIFIED", "🚫 BLOCKED", "ℹ️ INFO" — never a bare emoji, so the report stays
  greppable.
- Sections marked (OPTIONAL) — include only if relevant. A pure-CSS change may not
  need a Coexistence section beyond a one-liner. Cut what doesn't apply.
- Never overwrite an existing report — new file per run, `-2`/`-3` on same-day
  collision. Never number reports "round N" — a re-test replaces the prior status.
- Filename: qa-report-<slug>-<version>-<result-or-primary-issue>-<YYYY-MM-DD>.md
-->

# QA Report: {{Block Name}} — v{{version}}

**Date:** {{YYYY-MM-DD}}
**Site:** {{site_url}} — WordPress {{wp_version}}
**Slug:** {{slug}} · **Registered as:** `{{block.json name}}`
**Version under test:** {{version}} · **Baseline (wordpress.org):** {{baseline_version}}
**Registration guard:** `{{guard_name}}` {{— note if it looks misdirected}}

## Verdict

**Upgrade compatibility:** {{✅ PASS / ❌ FAIL / 🔍 UNVERIFIED}} — {{one line: does existing content survive}}
**Fresh installation:** {{✅ PASS / ❌ FAIL / 🔍 UNVERIFIED}} — {{one line: registration and defaults}}

**Overall:** {{✅ PASS / ⚠️ PARTIAL / ❌ FAIL}} ({{ship-ready / needs fixes / blocked}})

{{2–5 caveman sentences on why. Name the worst finding if there is one.}}

**Settings coverage: {{n}} of {{total}} controls checked. {{n}} Unverified (named below).**

## Phases

| Phase | Disposition | Note |
|---|---|---|
| P0 Identify & quarantine | {{✅/❌/🔍/🚫}} | |
| P1 Install baseline | {{✅/❌/🔍/🚫}} | |
| P2 Build fixture | {{✅/❌/🔍/🚫}} | |
| P3 Upgrade compatibility | {{✅/❌/🔍/🚫}} | |
| P4 Fresh installation | {{✅/❌/🔍/🚫}} | |
| P5 Security scan | {{✅/❌/🔍/🚫}} | |
| P6 Editor validation & lifecycle | {{✅/❌/🔍/🚫}} | |
| P7 Settings | {{✅/❌/🔍/🚫}} | |
| P8 Functionality & UX | {{✅/❌/🔍/🚫}} | |
| P9 Regression | {{✅/❌/🔍/🚫}} | |
| P10 Coexistence | {{✅/❌/🔍/🚫}} | |
| P11 Final check | {{✅/❌/🔍/🚫}} | |

A 🚫 phase gets a reason here, not silence.

## Findings

{{None.}} — or, per finding:

- **{{BLOCKER/HIGH/MEDIUM/LOW}} — {{title, one sentence, the behavior not a label}}:**
  {{What happens, where, why it matters to a user. Repro steps if not obvious.
  Actual vs Expected. Screenshot filename if visual.}}

## Security (P5)

One line per area. Mark "not applicable" rather than testing it if the plugin has no
such surface (no custom REST route, for instance) — that's the correct disposition, not
a gap. Not a threat-model writeup — that shape belongs elsewhere; this is the quick pass.

| Area | Result | Evidence |
|---|---|---|
| Sanitization & escaping (render_callback / generated CSS) | {{✅/❌/🔍}} | {{grep result or probe output}} |
| Capability / nonce checks | {{✅/❌/🔍/N/A}} | |
| REST / AJAX handling | {{✅/❌/🔍/N/A}} | {{"not applicable — no custom route registered" if so}} |
| XSS spot-check (unescaped input round-trip) | {{✅/❌/🔍}} | {{which attribute(s) tried, rendered output}} |
| Bundled dependency versions | {{✅/⚠️/🔍}} | {{anything conspicuously outdated, LOW unless a known issue applies}} |

{{Any confirmed, exploitable finding here is also listed under Findings as a BLOCKER — this
table is the evidence trail, Findings is where severity and the fix live. If a static hit
also exists in the P1 baseline's source, note that here and classify it as pre-existing in
Findings, not a regression.}}

## Intended changes vs. regressions

{{From the changelog and the attribute-registry diff between baseline and this
version. List what changed on purpose (ℹ️ INFO, cite the changelog line) separately
from anything that changed without explanation (investigate as a possible
regression).}}

## Settings tested

| Setting | Tab | Result | Evidence |
|---|---|---|---|
| {{name}} | {{General/Style/Advanced}} | {{✅/❌/🔍}} | {{probe output, screenshot, or diff — not prose}} |

## Unverified

{{List by name, with why: "not reached — ran out of time", "couldn't isolate from
an environment issue", etc. Silence here is not the same as Pass.}}

## Upgrade & regression detail

**Baseline fixture:** {{what was configured — preset, toggles, content}}
**After upgrade:** {{attributes intact? content valid? frontend matches?}}
**Against wp.org {{baseline_version}}:** {{what differs, and whether it's intended}}

## Coexistence (P10)

{{Registers and renders correctly with all single blocks active: yes/no.
Multi-block page save/reload/frontend: clean or not. Asset ownership re-check:
clean or not.}}

## Environment notes

{{Anything that looked like it might be core/theme/environment rather than the
block — and whether it also reproduced on the baseline.}}

## Test artifacts

{{Pages/posts created during testing, IDs and URLs — left for the user to clean up,
not deleted by this skill. Plugin activation state restored: yes/no.}}

## Next steps

{{Ship it. / Fix X before ship. / Blocked on Y.}}
