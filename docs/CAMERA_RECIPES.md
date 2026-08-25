# CAMERA RECIPES

Twenty base framings and thirteen modifier axes — the camera settings a
panel is actually rendered with.

This document exists because the style libraries speak in adjectives and
an image model satisfies an adjective by doing nothing. *Selective focus,
negative space, unusual placement* are all satisfied by an everything-sharp
frame. `85mm, f/2, focus on the eyes, shallow, backed away enough to
preserve facial perspective` has no such reading. It is also denser —
roughly 150 words carrying more instruction than a 1,000-character grammar
block — so it makes prompts smaller, not larger.

**It is read live.** Editing a row changes the picker, the prompt and the
panel's reader together, with no restart and no second list in the code.
That property is why one word could fix a style in an afternoon.

**The ID column is the contract.** Panels store the ID, not the name. Rename
a framing freely; changing an ID orphans every panel that chose it.

Its job, against the two documents beside it:

| document | holds | edit cadence |
|---|---|---|
| `CINEMATOGRAPHY_STYLES.md` | what a style is FOR — principle, mechanics, avoid | rarely; creative doctrine |
| **`CAMERA_RECIPES.md`** *(this)* | how a shot is actually taken | whenever calibrated against renders |
| `camera_defaults.json` | the silent fallback when nothing chose | never, once styles carry recipes |

---

## 1. Framings

One row per shot. A panel carries exactly one.

| ID | Desired framing / look | Focal length | Aperture | Camera relationship | Focus / DOF | Composition and resulting look |
|---|---|---:|---:|---|---|---|
| `epic-environmental-wide` | **Epic environmental wide** | 18–24mm | f/8–11 | Distant enough to establish the world | Deep | Environment dominates; character establishes scale; strong geography |
| `character-inside-a-large-environment` | **Character inside a large environment** | 24–32mm | f/5.6–8 | Fairly close to character | Medium/deep | Character remains important while environment carries story information |
| `classic-cinematic-medium-wide` | **Classic cinematic medium-wide** | 28–35mm | f/4–5.6 | Human-scale, moderately close | Medium | Balanced character/environment relationship; dimensional but not distorted |
| `deep-space-mise-en-scene` | **Deep-space mise-en-scène** | 24–32mm | f/8–11 | Close to a meaningful foreground plane | Deep | Deliberately distinct foreground, middle ground and background with story information in each |
| `immersive-inside-the-action` | **Immersive / inside the action** | 21–28mm | f/4–5.6 | Physically close to action | Medium/deep | Foreground interaction, strong motion through space, camera feels present |
| `natural-human-observation` | **Natural human observation** | 40–50mm | f/4–5.6 | Normal conversational distance | Medium | Restrained perspective; image feels witnessed rather than demonstrated |
| `character-focused-medium-shot` | **Character-focused medium shot** | 50–65mm | f/2.8–4 | Moderate distance | Medium/shallow | Character dominates while setting remains identifiable |
| `intimate-close-up` | **Intimate close-up** | 75–100mm | f/2–2.8 | Camera backed away | Shallow | Face dominates; environment simplifies; intimate controlled attention |
| `extreme-emotional-isolation` | **Extreme emotional isolation** | 85–135mm | f/1.4–2 | Distant enough to preserve facial perspective | Very shallow | Eyes/face become the perceptual world; environment dissolves |
| `three-character-dramatic-staging` | **Three-character dramatic staging** | 28–40mm | f/5.6–8 | Close enough to read expression and body language | Medium/deep | Characters can occupy different depths while their relationships remain readable |
| `over-the-shoulder-dialogue` | **Over-the-shoulder dialogue** | 40–65mm | f/2.8–4 | Just behind foreground actor | Medium/shallow | Foreground body establishes relationship; opposing face gets attention |
| `claustrophobic-interior` | **Claustrophobic interior** | 20–28mm | f/2.8–4 | Camera physically inside the constrained space | Medium | Walls and nearby objects press into frame; strong physical presence |
| `low-angle-heroic` | **Low-angle heroic** | 24–35mm | f/4–8 | Close and below waist height | Medium/deep | Foreground expands; subject gains monumentality and strong silhouette |
| `threatening-confrontational-proximity` | **Threatening / confrontational proximity** | 24–32mm | f/2.8–4 | Uncomfortably close | Medium | Perspective exaggeration makes presence immediate and aggressive |
| `elegant-portrait` | **Elegant portrait** | 75–100mm | f/2.8–4 | Backed away | Shallow/medium | Clean facial perspective and controlled separation |
| `compressed-crowd-city-pursuit` | **Compressed crowd / city / pursuit** | 100–200mm | f/4–5.6 | Far from subjects | Medium | People, vehicles and architecture appear densely stacked along camera axis |
| `distant-observational` | **Distant observational** | 135–300mm | f/4–8 | Very distant | Medium | Camera feels detached, hidden or unable to intervene |
| `flat-graphic-composition` | **Flat graphic composition** | 85–150mm | f/4–8 | Far back | Medium/deep | Reduced apparent depth; subjects and architecture become graphic layers |
| `subjective-poetic-character` | **Subjective / poetic character** | 50–100mm | f/1.4–2.8 | Position motivated by character perception | Selective | Negative space, partial framing and selective focus privilege emotional attention over geography |
| `fast-readable-action` | **Fast readable action** | 24–35mm | f/5.6–8 | Relatively close | Medium/deep | Protagonist, threat and escape route remain connected in one understandable spatial event |

---

## 2. Modifiers

Applied AFTER a framing is chosen, and only where the shot departs from
that framing's baseline — so a prompt carries deltas rather than a
restatement of the row it already named.

| Axis ID | Modifier | Setting | Effect |
|---|---|---|---|
| `focal-length` | **Focal length** | Go wider while maintaining subject size by moving closer | More foreground scale, stronger near/far relationships, greater physical presence |
|  |  | Go longer while maintaining subject size by moving farther away | Flatter-looking space, cleaner graphic relationships, greater detachment |
| `aperture` | **Aperture** | Open toward f/1.4–2 | Collapse attention onto one plane; reduce environmental readability |
|  |  | Close toward f/8–11 | Increase relational storytelling across multiple planes |
| `camera-distance` | **Camera distance** | Move physically closer | Stronger perspective, intimacy, foreground dominance, visceral movement |
|  |  | Move physically farther away | Reduced perspective differences, observational distance, apparent compression |
| `camera-height` | **Camera height** | 0.3–0.8m | Enlarged foreground, speed, monumentality, vulnerability to passing objects |
|  |  | 1.2–1.7m | Human-scale participation |
|  |  | 2–4m | More floor/ground geography, clearer blocking |
|  |  | Very high | Tactical, omniscient, pattern-oriented view |
| `camera-angle` | **Camera angle** | Frontal | Direct, graphic, confrontational, architectural |
|  |  | 3/4 | Dimensional, descriptive, useful for relationships |
|  |  | Profile | Graphic movement and opposition |
|  |  | Rear / following | Subjective discovery and audience alignment with character |
| `focus-strategy` | **Focus strategy** | Foreground focus | Immediate object/person becomes priority; deeper action becomes context |
|  |  | Character focus | Conventional narrative hierarchy |
|  |  | Background focus | Foreground becomes framing or obstruction |
|  |  | Deep focus | Audience can inspect several simultaneous story planes |
| `foreground-occupancy` | **Foreground occupancy** | Increase | Adds depth, occlusion and camera presence |
|  |  | Reduce | Cleaner, more objective or graphic composition |
| `negative-space` | **Negative space** | Increase | Isolation, anticipation, offscreen threat, emotional distance |
|  |  | Reduce | Pressure, density, immediacy |
| `shutter-angle` | **Shutter angle** | 45–90° | Crisp/staccato action |
|  |  | 180° | Normal cinematic motion |
|  |  | 270–360° | Smearing, panic, dream state |
| `lens-distortion` | **Lens distortion** | More corrected | Precision, architecture, formalism |
|  |  | More wide-angle character | Physicality, edge energy, imperfect immediacy |
| `lens-character` | **Lens character** | Modern / high correction | Controlled, precise, clean |
|  |  | Vintage / lower contrast | Flare, softer falloff, period or romantic optical personality |
| `camera-stability` | **Camera stability** | Locked | Formality, observation, tension through stillness |
|  |  | Dolly / track | Spatial revelation and controlled transformation of composition |
|  |  | Handheld / reactive | Human presence, instability, immediacy — only when dramatically motivated |
| `plane-separation` | **Plane separation** | Strong FG / MG / BG | Dimensional mise-en-scène and environmental storytelling |
|  |  | Deliberately collapsed | Graphic, compressed, confrontational or abstract composition |

---

## Changelog

- **2026-08-25** — Created. Sections 2 and 3 lifted verbatim from
  `docs/Cinematography/CINEMATIC_LENS_AND_FRAMING_RECIPES.md`, which stays
  as the authored reference (its sections 1 and 4 — what lens parameters
  affect, and the prompt format — are reading, not data). Stable IDs added;
  no wording changed. Count confirmed: **20 framings**, not 21.
