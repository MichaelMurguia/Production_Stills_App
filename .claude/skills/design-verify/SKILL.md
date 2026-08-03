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
