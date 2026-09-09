# Probes

Copy-paste `browser_evaluate` snippets, each placed next to the trap it exists to
catch. Prefer these over eyeballing the screen — a number is harder to fool yourself
with than an impression.

## The iframe hop — needed by every editor-side probe below

WP 6.3+ renders block DOM inside `iframe[name="editor-canvas"]`. Querying the
top-level `document` for block content returns `null` — which then reads as either a
phantom BLOCKER (element "missing") or a silent false pass (no error thrown, nothing
found means nothing wrong). Every probe that reads block DOM in the editor starts
with this:

```js
() => {
  const f = document.querySelector('iframe[name="editor-canvas"]');
  const d = f ? f.contentDocument : document;   // fall back for older/unframed editors
  return d; // then query against `d`, not `document`
}
```

## Registration identity

Confirm the block registered under the *actual* name from `block.json` — never
assume `<slug>/<slug>`:

```js
(expectedName) => {
  const t = wp.blocks.getBlockType(expectedName);
  return t ? { registered: true, name: t.name, title: t.title, category: t.category, icon: !!t.icon }
            : { registered: false };
}
```

Check the guard isn't silently deferring to something already active:

```js
(guardName) => wp.blocks.getBlockTypes().some(b => b.name === guardName)
// true means the guard's target IS registered — on a suite-installed site, this
// plugin's own registration would be skipped. On blocksnew.local (no suite
// installed) this will read false regardless — that's expected, not a pass on the
// guard logic itself. Report suite-conflict behavior as Unverified with that reason.
```

## Both inserters

```js
() => {
  const items = wp.data.select('core/block-editor').getInserterItems();
  return items.filter(i => i.name && i.name.includes('<slug-fragment>'))
              .map(i => ({ name: i.name, title: i.title, category: i.category }));
}
```
Run this for both the `/` slash inserter and the `+` block inserter's search —
they draw from the same registry, but confirm both UI paths surface it, since a
category or keyword mismatch can make one findable and not the other.

## Attribute inventory (the real source of truth)

`block.json` declares zero attributes on every one of these blocks — attributes are
registered in JS. Use the live registry, not static parsing:

```js
(blockName) => {
  const t = wp.blocks.getBlockType(blockName);
  if (!t) return { error: 'not registered' };
  return Object.fromEntries(
    Object.entries(t.attributes).map(([k, v]) => [k, { type: v.type, default: v.default }])
  );
}
```

Diff this dump between the baseline (P2) and the new ZIP (P3/P4) to find what's new
or removed — that's the real change surface, and it's usually a handful of names,
not the ~150 UI strings you'd get from grepping the bundle.

## Operate the control, then read the attribute back

Never verify a control by dispatching the attribute directly — that proves the
attribute round-trips and nothing about whether the control itself works. Read
before, drive the actual UI element (`browser_click` / `browser_select_option` /
`browser_type`), read after:

```js
(blockClientId) => wp.data.select('core/block-editor').getBlockAttributes(blockClientId)
```
If the value you expected to change is unchanged after operating the control, the
control is dead — that's a HIGH finding, not a skip.

`updateBlockAttributes()` is fine for cheaply re-establishing state after a reload;
it is never the thing that proves a control works.

## Save before navigating

```js
async () => {
  await wp.data.dispatch('core/editor').savePost();
  return wp.data.select('core/editor').didPostSaveRequestSucceed();
}
```
Only navigate after this returns `true`. An unsaved-changes `beforeunload` dialog
mid-navigation is unpredictable in Playwright.

## Validity after reload

```js
() => wp.data.select('core/block-editor').getBlocks()
  .map(b => ({ name: b.name, clientId: b.clientId, isValid: b.isValid }))
```
No `isValid: false`, and no block with `name === 'core/missing'`.

## Editor ↔ frontend parity

Same selector, same key set, both sides — turns "looks the same" into a diff:

```js
(sel) => {
  const f = document.querySelector('iframe[name="editor-canvas"]');
  const d = f ? f.contentDocument : document;
  const el = d.querySelector(sel);
  if (!el) return { found: false };
  const c = getComputedStyle(el), r = el.getBoundingClientRect();
  const pick = ['color', 'backgroundColor', 'fontSize', 'fontFamily', 'fontWeight',
                'lineHeight', 'textAlign', 'paddingTop', 'paddingBottom', 'paddingLeft',
                'paddingRight', 'borderTopWidth', 'borderTopColor', 'borderRadius',
                'display', 'justifyContent', 'alignItems'];
  return {
    found: true,
    rect: { w: Math.round(r.width), h: Math.round(r.height) },
    style: Object.fromEntries(pick.map(k => [k, c[k]])),
    childCount: el.querySelectorAll('*').length,
    text: el.innerText.replace(/\s+/g, ' ').trim().slice(0, 300),
  };
}
```
Run once in the editor (with the iframe hop) and once on the loaded frontend (no
hop needed there), then diff the two results. A `childCount` or `text` mismatch
usually means missing content; a style-key mismatch means visual divergence.

## Blank areas, clipping, overflow

```js
(sel) => {
  const el = document.querySelector(sel);
  if (!el) return { found: false };
  const r = el.getBoundingClientRect();
  const suspects = [...el.querySelectorAll('*')].filter(n => {
    const b = n.getBoundingClientRect(), s = getComputedStyle(n);
    return s.display !== 'none' && s.visibility !== 'hidden' && (
      b.width === 0 || b.height === 0 ||
      b.right > r.right + 1 || b.left < r.left - 1 ||
      (n.scrollHeight > n.clientHeight + 1 && s.overflowY === 'hidden')
    );
  }).slice(0, 20).map(n => ({ tag: n.tagName, cls: n.className }));
  return { found: true, blockHeight: Math.round(r.height), suspects };
}
```
Run on the frontend at three widths via `browser_resize` (desktop ~1440, tablet
~900, mobile ~480). A non-empty `suspects` list is worth a screenshot before you
report it — some are false positives (an intentionally hidden overflow menu, for
instance), but each one is worth a second look, not an automatic dismiss.

## Asset ownership (the trap-3 check)

Run on the frontend, after the last plugin activation, at P0-quarantine time and
again at P10 with everything reactivated:

```js
(slug) => [...document.querySelectorAll('script[src], link[rel="stylesheet"]')]
  .map(n => n.src || n.href)
  .filter(u => /\/plugins\/[^/]+\/(dist|assets)\//.test(u))
  .map(u => ({ url: u, owner: u.match(/\/plugins\/([^/]+)\//)[1] }))
```
Every `owner` should equal the slug under test (aside from core/theme assets). A
foreign owner means the evidence you're about to collect belongs to a different
plugin — treat that check as 🚫 BLOCKED, not as a passing frontend load.

## Generated CSS — check timing matters

```bash
# after save, BEFORE loading the frontend — a frontend visit regenerates the file
# regardless of whether save did its job, so checking after would always pass
stat -f '%m %z' "/Users/siamzafar/Local Sites/blocksnew/app/public/wp-content/uploads/eb-style/eb-style-<postID>.min.css"
grep -c '<the value you just set>' "/Users/siamzafar/Local Sites/blocksnew/app/public/wp-content/uploads/eb-style/eb-style-<postID>.min.css"
```

## Console and network

```
browser_console_messages   → filter to error-level from /plugins/<slug>/
browser_network_requests   → filter to 4xx/5xx from /plugins/<slug>/, and overall page status
```

## Security scan (P5)

Grounded in what this fleet's code actually does — verified on `table-of-contents-block`,
which renders through a `render_callback` and generates CSS from attribute values via the
shared style-handler — not a generic pentest checklist. Static patterns are a starting point
for judgment, not an automatic finding: a hit means "look closer," not "file a BLOCKER."

**Static — run against the unzipped plugin source (P0 already has it extracted):**

```bash
# Superglobals used without an obvious sanitizer nearby — read a few lines of
# context, since a nearby isset()/absint()/sanitize_*() call clears most of these
grep -n '\$_\(GET\|POST\|REQUEST\)\[' path/to/plugin/*.php path/to/plugin/includes/*.php

# Raw SQL concatenation instead of $wpdb->prepare() — rare on this fleet (most
# single blocks touch no custom tables at all), but worth one grep
grep -n '\$wpdb->query\|\$wpdb->get_' path/to/plugin/*.php path/to/plugin/includes/*.php

# Where attribute values reach output: a render_callback echoing $attributes
# without esc_html/esc_attr/esc_url, or the style-handler writing a color/text
# value into generated CSS without escaping it first
grep -n 'render_callback' path/to/plugin/*.php
grep -n 'esc_html\|esc_attr\|esc_url\|sanitize_' path/to/plugin/*.php path/to/plugin/includes/*.php
# — if render_callback exists but this second grep comes back empty, that's worth
# a closer read: an unescaped attribute value flowing to output is the concrete
# risk on this fleet (block.json declares zero attributes; everything server-side
# rendered is exactly where a JS-side escaping gap would surface in PHP output)

# REST/AJAX surface — only where the plugin actually has one; most single blocks
# have neither, and that's "not applicable", not a gap
grep -n 'register_rest_route\|wp_ajax_' path/to/plugin/*.php path/to/plugin/includes/*.php
# if found, confirm each has a permission_callback (REST) or a
# current_user_can()/check_ajax_referer() call (AJAX) — not just is_user_logged_in()
```

**Dynamic — fold into the P7 settings loop, don't run it separately:**

Among the realistic content you're already trying on a couple of text/URL-type attributes
(a title, a label, a link), include one deliberately adversarial value:

```
<script>document.title='xss'</script>
"><img src=x onerror="document.title='xss'">
```

Save, then check the rendered output — editor (through the iframe hop) and frontend both —
with the parity probe above, or directly:

```js
(sel) => {
  const el = document.querySelector(sel);
  return el ? el.innerHTML : null;
}
```

Expect to see the HTML-entity-encoded form (`&lt;script&gt;`) in the output, and the payload
never actually executing (`document.title` unchanged). If the raw tag comes through and
executes, that's a confirmed, exploitable finding — BLOCKER. If it's encoded, PASS, and you
have a specific evidence line for the report rather than an assumption.

**Dependency versions — quick spot-check, not a CVE database lookup:**

```bash
head -20 path/to/plugin/assets/js/*.js path/to/plugin/lib/**/*.js 2>/dev/null | grep -i 'version\|@license'
```
Flag anything that looks conspicuously old for a bundled library as worth a mention (LOW,
usually), not an automatic finding — bundling an old vendored copy isn't itself a
vulnerability without a known exploitable issue in that specific version.

**Baseline comparison — reuse the file, don't reinstall:**

For any static hit, check whether the same pattern already exists in the P1 baseline's
source before calling it a regression. The baseline ZIP is already on disk (P1 downloaded it,
or `eb_block_scan.py baseline <slug>` gives the URL directly) — grep that copy rather than
reinstalling the old version live just to re-run a static check.
