"""The mock engine — the whole pipeline at zero generation cost.

Debug tool (user request 2026-08-03): walk every stage — scan, bible,
breakdown, panels, repair, boards — without a single model call. Enabled
from Settings → Debug tools; while on, "MOCK ENGINE" appears in every
provider selector alongside the real engines.

Honesty rules: everything this module produces SAYS it is mock — images
carry a stamped MOCK RENDER band, text output states "mock" in its
sources and notes — so a dry-run artifact can never be mistaken for a
real research pass or render. Text derives deterministically from the
uploaded screenplay (real sluglines, real scene counts); images reuse
whatever the production's library already holds, else a drawn placeholder.
Image content deliberately does not matter — this tests the FLOW, never
generation quality.
"""
from __future__ import annotations

import random
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import paths, store

PROVIDER_ID = "mock"
LABEL = "MOCK ENGINE — no cost (debug)"
MODEL_NAME = "mock/static-content"
NOTES = "MOCK RENDER — static content, no model was called, no cost incurred."

_BASE_W = {"1K": 1280, "2K": 2560, "4K": 3840}


def _dims(image_size: str, aspect_ratio: str) -> tuple[int, int]:
    w = _BASE_W.get(image_size, 1280)
    try:
        aw, ah = (float(x) for x in aspect_ratio.split(":", 1))
        h = int(w * ah / aw)
    except (ValueError, ZeroDivisionError):
        h = int(w * 9 / 16)
    return w, max(64, h)


def _font(size: int):
    for p in ("C:/Windows/Fonts/bahnschrift.ttf", "C:/Windows/Fonts/arialbd.ttf",
              "C:/Windows/Fonts/arial.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _source_image() -> Path | None:
    """An existing image from THIS production's library — references first
    (any status; this is scaffolding, not canon), then existing takes."""
    pools: list[Path] = []
    if paths.REF_ORIGINALS.exists():
        pools += sorted(paths.REF_ORIGINALS.iterdir())
    if paths.BOARDS_DIR.exists():
        for d in sorted(paths.BOARDS_DIR.iterdir()):
            if d.is_dir():
                pools += sorted(d.glob("CAND-*.png"))
    pools = [p for p in pools if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")]
    return random.choice(pools) if pools else None


def render(prompt: str, ref_paths: list[Path], image_size: str,
           aspect_ratio: str, out_path: Path) -> str:
    """A cover-fit copy of an existing library image (or a drawn slate),
    stamped as MOCK, at the exact requested size — so size gates, slot
    maps, and the no-upscale verdicts all behave exactly as they would
    with a real render."""
    w, h = _dims(image_size, aspect_ratio)
    src = ref_paths[0] if ref_paths else _source_image()
    im = None
    if src is not None:
        try:
            with Image.open(src) as s:
                s = s.convert("RGB")
                scale = max(w / s.width, h / s.height)
                s = s.resize((max(1, round(s.width * scale)),
                              max(1, round(s.height * scale))), Image.LANCZOS)
                left, top = (s.width - w) // 2, (s.height - h) // 2
                im = s.crop((left, top, left + w, top + h))
        except Exception:
            im = None
    if im is None:
        im = Image.new("RGB", (w, h), (52, 48, 43))
    draw = ImageDraw.Draw(im)
    band_h = max(40, h // 14)
    draw.rectangle([0, h - band_h, w, h], fill=(20, 18, 16))
    draw.text((16, h - band_h + band_h // 5), "MOCK RENDER — NO COST",
              font=_font(max(18, band_h // 2)), fill=(216, 162, 74))
    snippet = " ".join((prompt or "").split())[:120]
    if snippet:
        draw.text((16, 14), snippet, font=_font(max(14, h // 60)),
                  fill=(232, 229, 221))
    im.save(out_path, "PNG")
    return NOTES


def repair_patch(src_path: Path, out_path: Path) -> None:
    """A full-size, visibly-different patch source for region repair. The
    repair pipeline composites this INSIDE the painted mask only — outside
    pixels are carried over bit-identical by generate.repair_region."""
    with Image.open(src_path) as s:
        base = s.convert("RGB")
    patch = Image.blend(base, Image.new("RGB", base.size, (216, 162, 74)), 0.45)
    draw = ImageDraw.Draw(patch)
    f = _font(max(20, base.height // 30))
    step = max(120, base.height // 6)
    for y in range(step // 2, base.height, step):
        draw.text((24, y), "MOCK REPAIR — NO COST", font=f, fill=(20, 18, 16))
    patch.save(out_path, "PNG")


# ------------------------------------------------------------- text passes

_CUE_RE = re.compile(r"^\s{0,40}([A-Z][A-Z0-9 .'\-]{1,28})(\s*\(.*\))?\s*$")
_CUE_NOISE = {"INT", "EXT", "CUT TO", "FADE IN", "FADE OUT", "DISSOLVE TO",
              "CONTINUED", "THE END", "TITLE", "SUPER", "DAY", "NIGHT",
              "LATER", "CONTINUOUS", "OMITTED"}


def _characters(max_n: int = 8) -> list[str]:
    """Dialogue-cue heuristic: short ALL-CAPS lines that repeat. Real names
    from the real screenplay — no model, no invention beyond the parse."""
    counts: dict[str, int] = {}
    for line in store.screenplay_text_cached().splitlines():
        m = _CUE_RE.match(line)
        if not m:
            continue
        name = m.group(1).strip(" .")
        if name in _CUE_NOISE or len(name) < 2 or name.split()[0] in ("INT", "EXT"):
            continue
        counts[name] = counts.get(name, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    return [n for n, c in ranked if c >= 3][:max_n]


def analyze() -> dict:
    """A Scene Scan-shaped analysis from the deterministic slugline parse.
    Locations and scene counts are REAL; the design worlds are stated
    placeholders for the user to rename or drop."""
    from . import insights
    loc = insights.locations()
    locs = loc.get("locations", [])
    if not locs:
        from .autofill import AutofillError
        raise AutofillError("MOCK SCAN needs an uploaded screenplay with "
                            "readable sluglines — upload one first.")
    ints = [l["location"] for l in locs if str(l.get("int_ext", "")).startswith("INT")]
    exts = [l["location"] for l in locs if l["location"] not in ints]
    environments = []
    if exts:
        environments.append({
            "name": "EXTERIORS", "keywords": ["exterior", "outside", "street"],
            "notes": "MOCK grouping — every EXT slugline; split into real "
                     "biomes on a real scan.", "locations": exts})
    if ints:
        environments.append({
            "name": "INTERIORS", "keywords": ["interior", "room", "inside"],
            "notes": "MOCK grouping — every INT slugline; split into real "
                     "worlds on a real scan.", "locations": ints})
    top = [l["location"] for l in
           sorted(locs, key=lambda l: -int(l.get("scenes", 0)))][:6]
    subjects = [{"name": n.title(), "kind": "CHARACTER",
                 "subtitle": "MOCK SUBJECT. FROM DIALOGUE CUES.",
                 "traits": [f"Speaks in the screenplay (cue '{n}').",
                            "Traits need a real scan or your own notes."]}
                for n in _characters()]
    return {
        "logline": f"MOCK READ — {len(locs)} slugline locations parsed "
                   "deterministically; no model was called.",
        "design_worlds": [
            {"name": "Principal World",
             "description": "MOCK placeholder — the protagonists' visual "
                            "culture. Rename or drop; a real scan replaces this.",
             "keywords": ["home", "principal"]},
            {"name": "Institutional World",
             "description": "MOCK placeholder — authority/industry visual "
                            "culture. Rename or drop; a real scan replaces this.",
             "keywords": ["official", "institution"]},
        ],
        "subjects": subjects,
        "environments": environments,
        "key_locations": top,
        "unresolved": ["MOCK SCAN — run a real engine before production "
                       "decisions; this pass only proves the flow."],
    }


def autofill_draft(subject_prompt: str, mode: str) -> dict:
    """A breakdown draft in the exact shape autofill._coerce expects.
    Citations point at real sluglines; every row is marked MOCK."""
    from . import insights
    locs = insights.locations().get("locations", [])
    want = subject_prompt.casefold()
    match = next((l for l in locs if l["location"].casefold() in want
                  or any(w in want for w in l["location"].casefold().split())),
                 locs[0] if locs else None)
    place = match["location"] if match else "the location"
    # A citation the screenplay actually contains. The docstring has always
    # claimed "citations point at real sluglines" and the string it built
    # was synthetic — which mattered from 2026-08-17, when SCRIPT_EXPLICIT
    # began being verified against the screenplay (review F21): a mock row
    # citing prose no document holds demotes to WEAK_INFERENCE/HOLD and the
    # zero-cost flow can no longer lock. Quoting the real heading keeps the
    # flow test exercising the verification instead of tripping over it.
    # The MOCK stamp lives in `rationale`, which is where an honesty stamp
    # belongs — `source` is the evidence, not the disclaimer.
    # The slugline reconstructed from the parse — "EXT. DEEP SPACE" — which
    # is literally a line in the screenplay and so survives verification.
    slug = ". ".join(x for x in [str((match or {}).get("int_ext", "")).strip(),
                                 place] if x).strip(". ")
    cite = slug if match else (
        f"MOCK CITATION — no slugline parse available for {place}")
    panels = [
        {"id": "P01", "title": f"{place.title()} — establishing",
         "purpose": "MOCK: establish the place, its light and its scale.",
         "required_objects": [place.lower()], "forbidden_objects": [],
         "scale": "WIDE", "allocation_percent": 50},
        {"id": "P02", "title": f"{place.title()} — working detail",
         "purpose": "MOCK: one corner in use — texture, wear, props.",
         "required_objects": [f"{place.lower()} detail"],
         "forbidden_objects": [], "scale": "DETAIL", "allocation_percent": 25},
        {"id": "P03", "title": f"{place.title()} — atmosphere",
         "purpose": "MOCK: the time-of-day and air of the place.",
         "required_objects": [f"{place.lower()} atmosphere"],
         "forbidden_objects": [], "scale": "MEDIUM", "allocation_percent": 25},
    ]
    ledger = [{"panel_id": p["id"], "object": o,
               "evidence_class": "SCRIPT_EXPLICIT", "source": cite,
               "confidence": 0.9, "status": "PASS",
               "rationale": "MOCK ROW — flow test only, not research."}
              for p in panels for o in p["required_objects"]]
    return {
        "subject": f"{place.title()} (MOCK breakdown)",
        "board_type": "LOCATION",
        "setting": {"int_ext": str((match or {}).get("int_ext", ""))[:10],
                    "location": place, "time_of_day": ""},
        "scene": ("MOCK DRAFT — panels and evidence were generated from the "
                  "slugline parse to exercise the flow at zero cost. Replace "
                  "with a real research pass before production."),
        "render_intent": "MOCK flow-test board; content is placeholder.",
        "panels": panels,
        "forbidden_elements": [],
        "evidence_ledger": ledger,
        "unresolved_questions": ["MOCK breakdown — re-run with a real engine "
                                 "for production research."],
    }


def scan_panel(spec: dict, panel: dict, ask: str, source: str) -> dict:
    """A screenplay scan at zero cost. Honesty-stamped MOCK, and every
    quote is taken LITERALLY from the source so the caller's verbatim
    check exercises its real path rather than being bypassed."""
    lines = [ln.strip() for ln in str(source).splitlines() if len(ln.strip()) > 30]
    finds = []
    for ln in lines[:3]:
        head = " ".join(ln.split()[:4]).rstrip(".,;:")
        finds.append({"object": head.lower(),
                      "detail": f"MOCK FIND — the scene mentions {head.lower()}.",
                      "quote": ln})
    return {"finds": finds,
            "note": f"MOCK SCAN for {ask.strip() or 'no specific ask'} — "
                    "no model was called."}


def composition_check(spec: dict, panel: dict, prompt: str,
                      anchor: dict) -> dict:
    """A composition verdict at zero cost, honesty-stamped: every note
    begins MOCK VERDICT. Real logic from real fields — a hero panel at an
    AERIAL/EXTREME_WIDE scale earns a genuine SUBJECT_PROMINENCE warning
    (that combination is exactly the GT40 failure this check exists for),
    so the flow test exercises both the clean and the warned branch."""
    resolved = str(panel.get("scale")
                   or store.camera_defaults().get("scale") or "").upper()
    findings = []
    suggested = {}
    if panel.get("composition_role") == "hero" and resolved in (
            "AERIAL", "EXTREME_WIDE"):
        findings.append({
            "axis": "SUBJECT_PROMINENCE", "severity": "WARN",
            "note": f"MOCK VERDICT — a hero panel at {resolved} renders its "
                    "subject small in a vast frame; the composition role "
                    "and the shot scale argue against each other.",
            "suggestion": "Tighten the shot so the hero subject carries "
                          "the frame."})
        suggested = {"scale": "WIDE"}
    else:
        findings.append({
            "axis": "COMPOSITION", "severity": "NOTE",
            "note": "MOCK VERDICT — no model was called; run a real "
                    "narrative engine for a production check."})
    if not anchor.get("matched"):
        findings.append({
            "axis": "ACTION_COVERAGE", "severity": "NOTE",
            "note": "MOCK VERDICT — the screenplay scene was not located; "
                    "a real check would judge against the sheet's scene "
                    "prose only."})
    return {"findings": findings, "suggested_camera": suggested,
            "purpose_amendment": ""}


_ORIENT_WORDS = [("side view", "SIDE"), ("profile", "SIDE"),
                 ("from behind", "REAR"), ("rear view", "REAR"),
                 ("head-on", "FRONT"), ("front view", "FRONT")]


def correction_deltas(reason: str, panel: dict) -> dict:
    """Deterministic keyword parse of a rejection reason into intake
    deltas, so the whole propose→apply flow is testable key-free. Real
    logic, honest scope: camera words map to axes; 'no X' clauses become
    forbids; other clauses become requires. corrections._coerce_deltas
    still validates and dedupes everything downstream."""
    low = " ".join(reason.lower().split())
    deltas: list[dict] = []
    for phrase, value in _ORIENT_WORDS:
        if phrase in low:
            deltas.append({"kind": "camera", "field": "camera_orientation",
                           "value": value})
            break
    for m in re.finditer(r"\bno ([a-z][a-z0-9 '\-]{2,40})", low):
        deltas.append({"kind": "forbid", "value": m.group(1).strip()})
    for clause in re.split(r"[.;]", reason):
        c = clause.strip()
        cl = c.lower()
        if not c or len(c) < 12:
            continue
        if any(p in cl for p, _ in _ORIENT_WORDS) or cl.startswith("no "):
            continue
        if any(w in cl for w in ("should", "must", "need", "would like")):
            deltas.append({"kind": "require", "value": c[:120]})
    return {"deltas": deltas}


def bible_markdown(answers: dict) -> str:
    """A bible draft in the exact section grammar bible.py parses, built
    from the interview answers (still BINDING — they land verbatim) and
    the mock environment grouping."""
    a = {k: str(v).strip() for k, v in (answers or {}).items()}
    analysis = store.load_wizard_analysis() or {}
    envs = analysis.get("environments") or []
    env_md = "\n".join(
        f"### {e.get('name', 'WORLD')}\n{e.get('notes', '')}\n"
        f"Keywords: {', '.join(e.get('keywords', []))}\n" for e in envs) or \
        "### PRINCIPAL WORLD\nMOCK environment — replace on a real draft.\n"
    worlds = analysis.get("design_worlds") or [
        {"name": "Principal World", "description": "MOCK placeholder language."}]
    world_md = "\n".join(
        f"## {w.get('name', 'World')}\n{w.get('description', '')}\n"
        f"Keywords: {', '.join(w.get('keywords', []))}\n" for w in worlds)
    return f"""## Status
MOCK DRAFT — assembled without a model call (debug flow test). The
director's interview answers below are binding; everything else is
placeholder to be replaced by a real draft.

## Overall Visual Identity
Touchstones (director, BINDING): {a.get('touchstones') or 'none given'}.
Never-list (director, BINDING): {a.get('never') or 'none given'}.

## Rendering Language
Medium (director, BINDING): {a.get('medium') or 'painterly production sketch'}.
Palette (director, BINDING): {a.get('palette') or 'warm neutral ground'}.
Visible brushwork, image-first hierarchy, concise labels. MOCK text.

## Lighting Language
MOCK — single practical-motivated key, honest shadow. Replace on a real draft.

## Character Presentation
MOCK — worn, specific, unglamorous. Replace on a real draft.

{world_md}
## Environments
{env_md}
## Core Material Language
### Principal World
MOCK — timber, mild steel, canvas. Replace on a real draft.

## Current Locked Scene-Specific Lessons
### (none yet)
Lessons accumulate from rejections.

## Drift Prevention Rule
Render only what the approved specification requires. Omit unspecified
content rather than filling space. (This rule is real even in a mock.)
"""


def mock_swatches(bible_text: str) -> list[dict]:
    """Deterministic swatch proposals for the debug engine: one group per
    parsed Design Language, colors cycled from a fixed film-plausible set,
    cites quoting the section's own first line. MOCK-stamped names so a
    mock proposal can never pass for a researched one."""
    from . import bible

    palette = ["#8A4B2E", "#3E4A52", "#C2803D", "#D8D3C4", "#1D6E63",
               "#5A564A", "#704838", "#2E3A44"]
    names = ["OXIDE RUST", "GUNMETAL BLUE", "SODIUM WORKLIGHT", "BONE WHITE",
             "LEDGER GREEN", "SOOT GREY", "LEATHER BROWN", "VOID STEEL"]
    langs = bible.design_language_names(
        bible.parse_sections(bible_text)) or ["PALETTE"]
    groups = []
    for li, lang in enumerate(langs[:4]):
        body = bible.parse_sections(bible_text).get(lang, "")
        line = next((ln.replace("**", "").strip("-* ").strip()
                     for ln in body.splitlines()
                     if ln.strip() and not ln.strip().lower()
                     .startswith("keywords:")), "from the saved bible")
        swatches = []
        for i in range(4):
            k = (li * 4 + i) % len(palette)
            swatches.append({"name": f"MOCK {names[k]}",
                             "hex": palette[k],
                             "pair_hex": "#5A564A" if i == 3 else None,
                             # One hero per language, same rule the real
                             # engine follows — the normalizer enforces it.
                             "hero": i == 0,
                             # A LABEL, the shape the real engine is asked
                             # for — "GRM green", not a clipped sentence.
                             # `line` still proves the section was read.
                             "cite": f"{lang.split()[0]} "
                                     f"{names[k].split()[-1].lower()}"
                                     if line else ""})
        groups.append({"language": lang, "swatches": swatches})
    return groups
