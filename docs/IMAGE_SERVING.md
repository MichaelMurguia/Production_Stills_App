# Image serving — display tiers & responsive imagery

How both apps serve images: keep the raw file as the archival truth, but hand
each display site the smallest image that still looks crisp (including at 2×
DPR). Two independent systems — the product app serves derivatives dynamically;
the storefront ships static responsive sets.

## Why

Renders are native 4K PNGs (20–40 MB, never upscaled — that rule is load-bearing
for the size gate). The app shows them almost everywhere at a fraction of that
size; the storefront showed ~92 MB of marketing PNGs at 150–380px. Serving the
raw file for a thumbnail-sized slot is the waste this system removes.

---

## Track A — the product app (`app/`)

### Tiers (`app/imaging.py`)

```
VARIANTS = {"thumb": (512, 80), "md": (1600, 82)}   # (max_edge_px, webp_quality)
# "full" = the source PNG, served untouched
```

- **thumb** — any site shown ≤~256px CSS (cards, filmstrips, rails, chips).
- **md** — mid displays: the staged hero (≤62vh), board drill-ins (≤72vh),
  board-frame slots.
- **full** — where real pixels are consumed: the lightbox at 100%, the crop
  tool, the repair (inpaint) canvas.

Derivatives are **WebP** — ~30% smaller than JPEG, universal browser support,
and irrelevant to `store.RENDER_SAFE_FORMATS` because they are **display-only**:
a derivative never feeds a render engine and never feeds a size gate.

### The helper — `imaging.variant_path(src, cache, max_edge, quality)`

One builder, used by candidates and references alike. Lazy build with an **mtime
guard** (rebuilds when the source is newer), **never upscales** (a small source
is transcoded, not enlarged), and on **any failure returns `src`** — a display
request degrades to the full image, never a 404. `imaging.warm(src, cache_for)`
pre-builds every tier.

### Resolvers & caching

| Kind | Resolver | Cache file | Warmed |
|---|---|---|---|
| Candidate render / board | `generate.candidate_variant_path(spec, cand, size)` | `boards/<SPEC>/<CAND>.{thumb,md}.webp` beside the PNG | eagerly at render / board-assembly / repair / re-render write (`warm_candidate_variants`), lazy fallback on request |
| Reference | `store.reference_image_path(ref, size=…)` | `references/thumbs/<REF>.{thumb,md}.webp` | eagerly at intake / image-replace (`_warm_reference_variants`), lazy fallback |

`size="full"` (or an unknown tier) returns the raw path — so every existing
generation caller (`_reference_image_paths`, crop/repair sources) is unaffected.

### Endpoints (`main.py`)

Both image routes take `?size=thumb|md|full` (default `full`); `?thumb=1` /
`?thumb=true` stay as a back-compat alias for `size=thumb`.

- `GET /api/specs/{spec}/candidates/{cand}/image?size=…`
- `GET /api/references/{ref}/image?size=…`

### Frontend contract (`app/static/app.js`)

Each `<img>` requests the tier its slot needs. **When adding a display site,
pick a tier by rendered size:** ≤256px → `?size=thumb`; a mid pane → `?size=md`;
a zoom/pixel-edit surface → no param (full). The lightbox `item.src`, crop and
repair sources are deliberately parameterless. `renderCard(…, size)` takes a
tier arg (grid cards `thumb`, the board-solo drill-in `md`).

### Deletion

`generate.delete_candidate` unlinks every `<CAND>.*.webp` variant (plus the
legacy `<CAND>.thumb.jpg`); `store.delete_reference` already globs `<REF>.*`.
Add any new tier's suffix to the candidate unlink loop if the set grows.

### The size gate is NOT affected

`assemble.slot_map` / `legal_openai_size` read `record["width"/"height"]` — the
render's real dimensions — never a served file. Derivatives are display-only, so
"never upscaled" and TOO_SMALL verdicts are unchanged.

---

## Track B — the storefront (`storefront/`)

Static marketing stills, not dynamic renders — so a build step + `srcset`.

### Build — `storefront/scripts/build_images.py`

For each source in `static/img/` (`p01`–`p15`, `board-0001`), emits
`web/<name>-w{400,800,1200,1600}.webp` (never upscaling) plus one
`web/board-0001-og.jpg` (1200×630 cover) for social cards. Idempotent; rerun
after adding or replacing a source, and commit the derivatives. The raw PNGs
stay in `static/img/` **for regeneration only** — no page references them.

### Templates

Pages use `srcset`/`sizes` against the WebP set with **literal** paths (the
served-asset test in `test_store_tokens.py` statically verifies every `src`).
`og:image` / `twitter:image` / JSON-LD use the **JPEG** card (crawlers support
WebP unevenly); the coming-soon backdrop uses `board-0001-w1600.webp`.

### Guardrails — `storefront/tests/test_store_images.py`

Fails the build if any template references a raw multi-MB still, if a referenced
derivative is missing from disk, or if the build script upscales / stops
emitting WebP. Logged in `STORE_DESIGN_SYSTEM.md` → Non-canon queue.

---

## Regenerating derivatives

- **App**: automatic. Nothing to run — variants warm at write and self-heal via
  the lazy path; the mtime guard rebuilds them if a source PNG is replaced.
- **Storefront**: `cd storefront && python scripts/build_images.py`, then commit
  `static/img/web/`.

## Verifying

- App: `python -m unittest tests.test_image_variants` and, live, confirm the
  takes strip pulls `*.thumb.webp`, the staged hero `*.md.webp`, and only the
  lightbox the full PNG (DevTools → Network).
- Store: `cd storefront && python -m unittest tests.test_store_images`; boot the
  store and confirm the landing page serves only `web/*.webp` (no raw PNG).
