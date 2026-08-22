"""Generate the rendering-style calibration prompts.

Nine rendering styles x three locked scenes = 27 generation prompts, in
the shape of the user's own CINEMATOGRAPHY_24_PROMPTS_v2.md.

That document's premise, inverted. Its baseline reads "the rendering
language is LOCKED across the entire cinematography calibration set —
cinematography may change; rendering style may not." Here the rendering
style is the ONLY thing allowed to change, and subject, camera, light,
blocking and palette are locked instead. Otherwise the picker's three
frames would differ in five ways at once and prove nothing about the
medium.

The style text is READ from docs/RENDERING_STYLES.md rather than copied
here. That document already feeds the picker, the Bible drafter and every
render prompt; a fourth hand-maintained copy of a style's mechanics is
exactly the drift this codebase keeps finding. Edit the document, re-run
this, and the calibration set follows.

    python -m scripts.render_style_prompts [out.md]
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import style_docs  # noqa: E402

OUT_DEFAULT = ROOT / "docs" / "RENDERING_STYLE_PROMPTS.md"

# One subject, three framings. The vehicle is the same vehicle in all 27
# images and the driver is the same driver, so the nine styles read as one
# comparison rather than twenty-seven unrelated pictures — the property
# that makes the texture set legible in the picker.
SCENES = [
    ("A", "Object", """A single six-wheeled desert hauler, three-quarter front view, \
standing alone on flat neutral ground with no environment behind it.

The vehicle is heavy, purpose-built and utilitarian: a high armoured cab, an \
open flatbed rear, six oversized run-flat wheels, external roll cage, stowed \
tools and fuel cans lashed along the flank, one spare wheel mounted behind the \
cab. It has been used and maintained, not restored and not wrecked.

The whole vehicle is inside the frame with clear space around it. The form is \
the subject: proportion, structure, mechanical logic and silhouette."""),
    ("B", "Figure", """The hauler's driver, waist-up, standing beside the open cab \
door with one hand on the frame and a wrench in the other.

Late thirties, weathered, close-cropped hair, a heavy canvas work jacket over a \
dark undershirt, gloves pushed into a pocket. Looking off-frame at something \
that has just caught their attention.

The cab door and part of the armoured flank are visible behind them, close \
enough to read as the same vehicle. The face and hands are the subject."""),
    ("C", "Environment", """The same hauler crossing a dry lake bed at dusk, small \
in a wide frame, trailing a low plume of dust.

Cracked pale ground running to a distant ridge line. A high thin sky with the \
last light behind the ridge. No other vehicles, no structures, no figures.

Scale, distance and air are the subject: how far away the vehicle is, and how \
much atmosphere sits between it and the camera."""),
]

CONTRACT = """OUTPUT CONTRACT

Generate exactly ONE image.

Aspect ratio: 16:9.

The image fills the entire canvas.

No typography.
No labels.
No captions.
No borders.
No split screen.
No panels.
No storyboard.
No contact sheet.
No mood board.
No poster design.
No multiple moments.
No inset images.
No watermarks.

(Style 09, Technical Blueprint, is the single exception to "no typography":
its dimension annotations are part of the medium and are permitted.)"""

BASELINE = """LOCKED SUBJECT AND CINEMATOGRAPHY BASELINE

The rendering style is the ONLY variable in this calibration set. Everything
else is locked across all nine styles and must not change to express a
medium.

Locked:
- the vehicle: same design, same proportions, same fittings, same wear state
- the driver: same face, apparent age, build, hair and costume
- the scene, the moment, and what is happening
- camera position, framing, and subject-to-camera distance
- the light: same direction, same quality, same time of day
- the palette: same hues and the same value key
- the surface condition of the world: used and maintained, not pristine and
  not derelict

Do not redesign the vehicle, the driver, the location or the lighting in
order to express the rendering style. If two images in this set differ in
more than the MEDIUM, the calibration has failed.

Express the rendering style ONLY through:
- medium and material of the picture itself
- mark, stroke, line and edge quality
- how form is described: mass, outline, tone, hatching, or geometry
- surface finish of the artwork
- degree and kind of detail
- how colour is laid down, if at all"""

PRECEDENCE = """PRECEDENCE

Where the scene description calls for something the rendering style forbids,
THE STYLE WINS — the style is what is being calibrated.

Scene C describes dusk atmosphere and Scene B describes a lit face. A style
whose own avoid list refuses lighting, atmosphere or environment (Technical
Blueprint, Industrial Design) must render the same SUBJECT under its own
rules instead: the same vehicle at the same distance, drawn as that medium
draws things. Do not add atmosphere to satisfy the scene, and do not abandon
the subject to satisfy the style."""

CONTINUITY = """CALIBRATION CONTINUITY

This is a controlled rendering-medium test. The vehicle, the driver, the
location, the moment, the camera and the light are locked across all nine
rendering styles.

Do not invent a different vehicle, a different driver or a different location
for another style."""


def block(style: dict, code: str, label: str, scene: str) -> str:
    mech = "\n".join(f"- {m}" for m in style["mechanics"])
    avoid = "\n".join(style["avoid"]) or "nothing stated"
    return f"""```text
{CONTRACT}

{BASELINE}

{PRECEDENCE}

{CONTINUITY}

SCENE {code} — {label.upper()}

{scene}

RENDERING STYLE

{style['name'].upper()} — {style['subtitle'].upper()}

{style['description']}

Operating principle: {style['principle']}

Visual mechanics:
{mech}

{style['prompt']}

Avoid:
{avoid}
```"""


def build() -> str:
    styles = style_docs.styles("rendering")
    out = [
        "# RENDERING STYLE CALIBRATION — 27 LOCKED GENERATION PROMPTS",
        "",
        "Nine rendering styles x three locked standard scenes.",
        "",
        "**A — Object:** the hauler alone, three-quarter front, neutral ground  ",
        "**B — Figure:** the driver, waist-up, at the open cab door  ",
        "**C — Environment:** the hauler crossing a dry lake bed at dusk",
        "",
        "The subject, camera, light and palette blocks are identical across all "
        "nine styles. Only the rendering medium changes.",
        "",
        "Generated from `docs/RENDERING_STYLES.md` by "
        "`scripts/render_style_prompts.py` — edit the document and re-run, "
        "never edit this file. It is the same nine styles the picker shows and "
        "the Art Direction Bible is written from, so a prompt here cannot "
        "describe a style the app does not have.",
        "",
        "Save each render as `<Scene>_<Style>.png` — `Object_Production_Painting.png`, "
        "`Figure_Ink_Wash.png`, `Environment_Technical_Blueprint.png` — and the "
        "app's plate importer will map them without a rule per filename.",
        "",
        "---",
        "",
    ]
    for st in styles:
        out += [f"# {st['n']:02d}. {st['name']} — {st['subtitle']}", ""]
        for code, label, scene in SCENES:
            out += [f"## {st['n']:02d}-{code} — {label} — {st['name']}", "",
                    block(st, code, label, scene), ""]
        out += ["---", ""]
    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    dest = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else OUT_DEFAULT
    text = build()
    dest.write_text(text, encoding="utf-8")
    n = text.count("```text")
    print(f"wrote {dest} — {n} prompts, {len(text.splitlines())} lines")
