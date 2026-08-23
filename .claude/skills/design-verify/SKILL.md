---
name: design-verify
description: Run the mock-parity verification loop on an app view — seeded headless capture at design width, mock comparison, token assertions, capture sent to the user before any release. MANDATORY for every UI-touching change (CLAUDE.md).
---

# design-verify — the mock-parity loop, mechanized

Run this loop for ANY change to app/static/{styles.css,index.html,app.js}
that a user can see. It encodes the failures that actually happened
(2026-08-04: five user-caught misses, then two more interpretation
failures) so they cannot recur. The written process lives in
DESIGN_SYSTEM.md → "Verifying against mocks"; this skill is its
executable form.

## 0. Authority order — settle this BEFORE writing CSS

1. **A delivered `*_SNIPPET.html`** (repo root or design_mocks/) is the
   authority for its element. Implement by TRANSLITERATION: same
   structure, same values, every hex mapped to its existing token
   (#0f1114=--field, #15181b=--bg2, #23272c=--line-soft, #2b3037=--line,
   #e0a33f=--accent, #eceef0=--ink, #9aa1a8=--ink-dim, #6b7278=--ink-faint).
   Never reinterpret a snippet. Delete it when done, like a plan file.
2. **The mock's plain reading** beats any clever theory you derive from
   pixel-sampling. Sampling is for extracting VALUES (a hex, a px), never
   for constructing structure the eye doesn't see. If your sampled theory
   contradicts what the mock obviously looks like, the look wins.
3. **The written rule** beats code you find; **the user's stated hex/value**
   beats your sample.

## 1. Seed — a clean install, no leaks

```bash
SCRATCH=<session scratchpad>; mkdir -p "$SCRATCH/mockhome"
cd <repo> && OPENAI_API_KEY="" GEMINI_API_KEY="" \
  SCREENBOARD_HOME="$SCRATCH/mockhome" \
  python -m uvicorn app.main:app --port 87xx > "$SCRATCH/uv.log" 2>&1 &
sleep 4
curl -s -X POST localhost:87xx/api/projects -H "Content-Type: application/json" -d '{"name":"Parity Demo"}'
```

- Env keys MUST be blanked — a shell's OPENAI_API_KEY silently flips
  two-lives screens to their configured state (this happened).
- Seed whatever state the mock shows (a production, a locked sheet,
  candidates…) via the API, never by hand-editing files.

## 2. Capture — Edge headless at the design width

```bash
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" \
  --headless=new --disable-gpu --hide-scrollbars \
  --window-size=1420,<tall enough> --virtual-time-budget=9000 \
  --screenshot="$(cygpath -w "$SCRATCH/shot.png")" \
  "http://127.0.0.1:87xx/#<view>"
```

Mocks are authored at 1360px content width; 1420 viewport ≈ 1360 content
+ chrome. `--virtual-time-budget` lets the SPA finish its fetches.

## 2b. Drive it — when the view needs interaction, or you need numbers

A URL screenshot only reaches what a cold boot renders. Anything behind a
tab, a subview, a modal, or a scroll needs a driver — and driving also
lets you MEASURE instead of eyeballing, which is how you catch a wrong
token that looks right.

Edge with a debugging port, then CDP over `websockets` (already installed;
`websocket-client` is not):

```bash
"/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"   --headless=new --disable-gpu --hide-scrollbars   --remote-debugging-port=9333 --user-data-dir="$SCRATCH/edge"   --window-size=1420,1000 "http://127.0.0.1:87xx/" &
```

Always a **fresh `--user-data-dir`** and a port nothing else holds; a
reused profile brings back a stale session and you verify the wrong state.

```python
import asyncio, base64, json, urllib.request, websockets

def target():
    for t in json.load(urllib.request.urlopen("http://127.0.0.1:9333/json")):
        if t["type"] == "page":
            return t["webSocketDebuggerUrl"]

async def main():
    n = 0
    async with websockets.connect(target(), max_size=200_000_000) as ws:
        async def cmd(method, **params):
            nonlocal n; n += 1
            await ws.send(json.dumps({"id": n, "method": method, "params": params}))
            while True:
                m = json.loads(await ws.recv())
                if m.get("id") == n:
                    if "error" in m: raise SystemExit(f"{method}: {m['error']}")
                    return m.get("result", {})
        async def js(expr):
            r = await cmd("Runtime.evaluate", expression=expr,
                          awaitPromise=True, returnByValue=True)
            return r.get("result", {}).get("value")
        await cmd("Page.navigate", url="http://127.0.0.1:87xx/")
        await asyncio.sleep(4)          # let the SPA finish its fetches
asyncio.run(main())
```

`max_size` matters — a full-page screenshot exceeds the default frame cap
and the socket dies mid-capture.

**Reach the view the way a user does.** Call the app's own navigation
rather than faking state:

```python
await js("showView('settings')")
await js("document.querySelector('#settings-subnav button[data-sub=debug]').click()")
await asyncio.sleep(1.5)
```

**Clip coordinates are PAGE coordinates.** `getBoundingClientRect()` is
viewport-relative, so a clip built from it captures the wrong region once
the page has scrolled — silently, and the screenshot looks plausible.
Add the scroll offsets:

```python
box = await js("""(() => {
  const el = document.querySelector('#target');
  el.scrollIntoView({block:'center'});
  const r = el.closest('.panel').getBoundingClientRect(), cs = getComputedStyle(el);
  return {x: Math.round(r.x + scrollX - 16), y: Math.round(r.y + scrollY - 16),
          w: Math.round(r.width + 32),      h: Math.round(r.height + 32),
          font: cs.fontFamily.split(',')[0], size: cs.fontSize,
          color: cs.color, bg: cs.backgroundColor, border: cs.borderColor};
})()""")
shot = await cmd("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                 clip={"x": box["x"], "y": box["y"], "width": box["w"],
                       "height": box["h"], "scale": 2})
open(out, "wb").write(base64.b64decode(shot["data"]))
```

**A zero-size rect means hidden, not missing.** An element can be in the
DOM and unmeasurable because an ancestor is `display:none`. Do not
conclude "the control did not render" — walk the chain and find out which
ancestor:

```python
await js("""(() => {
  let e = document.querySelector('#target'), out = [];
  while (e && e.tagName !== 'BODY') {
    const cs = getComputedStyle(e);
    out.push(`${e.tagName}.${e.className} d=${cs.display} h=${e.getBoundingClientRect().height}`);
    e = e.parentElement;
  }
  return out.join(' | ');
})()""")
```

**Measure, then read the picture.** `getComputedStyle` settles token
questions a screenshot cannot: `rgb(154,161,168)` IS `--ink-dim`,
`rgb(43,48,55)` IS `--line`. Confirm the value, then still LOOK at the
capture — the measurement proves the token, the eye catches the copy that
contradicts the button beside it. (That is a real one: a panel read
"edits live on this install only" directly above a *Publish to every
studio* button. Every token was correct.)

Kill the browser and the servers when done; an orphaned Edge holding a
debug port makes the next session's capture stale.

## 3. Compare — eyes first, then pixels

1. Read the capture AND the mock side by side (the Read tool renders
   PNGs). Walk the mock top-to-bottom listing every element; check each
   in the capture: containment, grounds, borders, sizes, weights,
   spacing, voice (Courier vs Archivo). The classic failure is a
   dropped wrapper; the second-classic is a wrong ground layer.
2. Pixel-sample the mock (PIL getpixel) for exact values only.
3. Optional diff artifact (mock | build | difference) for the commit,
   as design_mocks/<mock>-parity-<date>.png.

## 4. Assert tokens mechanically

`python -m unittest tests.test_design_tokens` — the standing suite that
asserts styles.css declarations for every canonized component. When you
build or change a component, ADD ITS ASSERTIONS in the same commit
(selector → the declarations the mock/snippet states). CI runs this on
every push; a drift that would slip past eyes fails the build.

## 5. Show, then ship

For anything visually changed: crop the capture to the changed region
and SendUserFile it BEFORE releasing, with one line saying what to
check. A bad read must cost a reply, not a release. Then: suites green →
VERSION bump → commit code → stage_release AFTER the commit (the zip
archives HEAD — running it before the commit ships stale content; this
happened twice) → commit zips → push → fleet update → verify tenant
version.

## The store (`storefront/`) — same loop, different subject

Ruled 2026-08-06: store UI is not exempt. Authority is
`STORE_DESIGN_SYSTEM.md` (a different system — its amber has four
sanctioned roles, and the app's scarcity rule does NOT apply here).

**Seed and boot** a throwaway store rather than the app:

```bash
SCRATCH=<session scratchpad>
cd <repo>/storefront && DATABASE_URL="sqlite:///$(cygpath -m "$SCRATCH")/store.db" \
  SESSION_SECRET=demo ADMIN_EXPORT_TOKEN=tok-demo OWNER_EMAILS=you@example.com \
  TRIAL_DAYS=14 STRIPE_SECRET_KEY=sk_test_demo STRIPE_PRICE_CLOUD_PERSONAL=price_demo \
  BASE_URL=http://127.0.0.1:8110 python -m uvicorn app.main:app --port 8110 &
```

- Grep the log for `10048` before trusting a capture — a leaked server
  from an earlier session on the same port will serve you STALE UI and
  you will "verify" the wrong build (this happened).
- Set the Stripe/price vars to open the paid paths; leave them unset to
  capture the stated gates instead. Both lives deserve a look.
- Owner-only surfaces need a session: mint one with
  `auth.make_session(email)` and set it via CDP `Network.setCookie`
  (`sb_account`), or drive the page with `TestClient`.

**Capture** at 1420 wide (the store wraps at 1180 + chrome), same Edge
recipe as the app. **Compare** against `design_mocks/` where a store mock
exists; where none does, compare against the system's rules directly —
fills counted, kickers one per section, trait lists with their one
tradeoff, gates stated not errored.

**Assert** `storefront/tests/test_store_tokens.py` (the store's standing
contracts — every token used must be defined; a `var(--x)` with no `--x`
renders as inherited ink and silently drops a designer's ruling, which is
exactly how `--hold` was lost for five days).

**Log** the feature as a row in `STORE_DESIGN_SYSTEM.md` →
`## Non-canon — awaiting review`, in the same commit, naming what the
designer should rule on. That table is the queue a review reads; the
changelog below it is history. Logging to the changelog alone hides the
work from the review (it did, 2026-08-06).

## Interaction states a screenshot cannot show — check by reading code

- No focusable/editable element inside chrome copy (caret risk).
- `user-select: none` on chrome (heroes, banners, marquees, chips);
  real content stays selectable.
- Animations: `steps(1)` for carets (fading reads as a glitch),
  duplicated sequences + `-50%` + `width: max-content` + track `gap`
  (never per-tile margins) for marquees, and every animation under
  `prefers-reduced-motion: reduce`.
- New tabs/popups only inside a user's click gesture, never automatic —
  a focus-stolen tab reads as "the modal never appeared" (happened).
