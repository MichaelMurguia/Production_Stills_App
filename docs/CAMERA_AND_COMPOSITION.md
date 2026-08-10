# Camera & composition — tech reference

How the app turns a chosen camera term into a render directive. Structured,
app-authored, prominently placed, and stated to outrank the reference images —
because a render told "High Camera Angle" as free text was ignored (the model
under-weights terse composition tokens, and the references anchor the framing).

## The four axes

Per-panel fields (all optional), each resolved `panel value → production
default → unset`:

| Field | Values |
|---|---|
| `camera_angle` | `EYE_LEVEL · LOW · HIGH · BIRDS_EYE · WORMS_EYE` |
| `camera_lens` | a focal length string `^\d{1,3}MM$` — presets 18/24/35/50/85/135 mm **plus any custom value** (e.g. `28MM`, `200MM`) |
| `camera_tilt` | `LEVEL · DUTCH` (`LEVEL` is intentionally silent) |
| `scale` (shot) | `AERIAL · EXTREME_WIDE · WIDE · MEDIUM · CLOSE · EXTREME_CLOSE · MACRO · MICRO` |

The vocabulary and validation live in **`store.CAMERA_FIELDS`** (sets for the
enum axes, a regex `store._LENS_RE` for the lens); `store._camera_valid` /
`_clean_camera_fields` normalise (upper-case) and reject bad values.

## Defaults — the production baseline

A new production starts from **`store.CAMERA_BASELINE`** = `EYE_LEVEL · 24MM ·
LEVEL · WIDE`. `store.camera_defaults()` returns `{**CAMERA_BASELINE,
**data/camera_defaults.json}` — so a production with nothing set still carries
the house grammar, and every panel inherits it unless it overrides an axis.
`store.save_camera_defaults()` writes the file (its own file so it never races
`app_state` counter writes).

## Prompt injection

`generate._camera_block(panel)` (in `generate.py`) resolves each axis
(panel-or-default), expands it to an authored sentence, and emits a **CAMERA**
block placed right after `PANEL PURPOSE` in `compile_panel_prompt` — high in the
prompt, and closing with the override line: *"where an attached reference shows a
different angle, lens, or framing, follow THIS, not the reference's composition;
references anchor identity, materials, colour and medium, never the camera."*

- Enum phrasing: `CAMERA_ANGLE_PHRASING`, `CAMERA_TILT_PHRASING`, `SCALE_PHRASING`.
- Lens phrasing: **`generate._lens_phrasing(value)`** — one source of truth for
  presets *and* custom focal lengths; it reads the millimetres and derives the
  perspective character (≤20 ultra-wide, ≤35 wide, ≤60 normal, ≤105 short-tele,
  else telephoto). `generate._LEGACY_LENS` maps the pre-2026-08-10 words
  (`WIDE→24MM`, `NORMAL→50MM`, `TELEPHOTO→135MM`) so old settings still speak.
- Emit order: shot, lens, angle, tilt. An all-empty camera contributes nothing.

This block replaced the old terse `SCALE:`/`COMPOSITION ROLE:` tail.

## Per-panel edits between takes

`store.amend_panel_camera(spec_id, panel_id, fields)` sets a panel's camera from
the workbench without unlocking — the same controlled-edit contract as
`amend_panel_purpose`: an APPROVED take was composed at its camera and **freezes**
it (reject first); otherwise the lock **re-stamps** and the change is journaled. A
present field with an empty value clears it back to the production default.

## Endpoints (`main.py`)

- `GET /api/camera-defaults` — the production default (baseline-merged).
- `POST /api/camera-defaults` — replace it (422 on an invalid value).
- `POST /api/specs/{spec}/panels/{pid}/camera` → `amend_panel_camera`.

## UI — three surfaces, one control (`app/static/app.js`)

`cameraRow(prefix, obj, blank, disabled)` renders a labelled row of four selects;
`readCameraFields(prefix, root)` reads them back (resolving a Custom lens to
`"<n>MM"`); `wireCameraRow(prefix, root, onChange)` toggles the Custom
focal-length input and fires `onChange`. Vocabulary consts: `CAMERA_ANGLES`,
`CAMERA_LENSES`, `CAMERA_TILTS`, `SHOT_SCALES`, `CAMERA_AXES` (near `TIMES_OF_DAY`).

| Surface | Prefix | Blank? | Persists |
|---|---|---|---|
| **Camera grammar card** — leads the Look Interview (`index.html` step 1, `#cam-default-row`) | `dcam` | no — always concrete (the production default) | POST `/api/camera-defaults` on change |
| **Breakdown sheet editor** — a per-panel row | `pcam` | `— from bible —` | serialised into the panel on sheet save (`...readCameraFields("pcam", row)`) |
| **Panels workbench** — inline between-takes control | `cam` | `— from bible —` | POST `/panels/{id}/camera` on change; disabled when a take is approved |

The lens select adds a **Custom…** option that reveals an inline `type=number`
mm field (`.cam-lens` / `.cam-lens-mm`, marked `UNCANONIZED` in styles.css).

## Tests & extension

- `tests/test_camera.py` — resolution, baseline, every enum + focal length has
  phrasing, legacy migration, amend (lock re-stamp / journal / frozen), and the
  three-surface JS/HTML wiring.
- **Add an angle/tilt/shot value:** extend the set in `store.CAMERA_FIELDS`, add
  its phrasing dict entry in `generate.py`, and the `[value, label]` pair in the
  matching `app.js` const. **Lens is open-ended** — any `NNmm` already works, so
  new "presets" are just JS label entries.
