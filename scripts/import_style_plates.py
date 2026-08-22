"""Import rendered style plates into the picker.

    python -m scripts.import_style_plates <library> <folder> [--alias A=B ...]

A library's picker shows three frames per style, read from
`app/static/style-plates/index.json`. This turns a folder of renders into
those frames: it maps each file to a style and a scene, converts to webp at
the plate width, and rewrites the manifest — leaving every other library's
entries alone.

Naming is `<Scene>_<Style>.png`, e.g. `Object_Production_Painting.png`.
The scene half decides the slot, in first-seen alphabetical order, so the
three frames of every style are in the same order as each other.

It REFUSES rather than guesses. An unmatched style name, a scene that
would claim a slot twice, or a style the document does not define stops
the run with the offending filename — a mismapped plate is a picture of
the wrong thing under the right label, which is worse than no picture.
Genuine oddities take an explicit `--alias Industrial_Use=Industrial Grime`
rather than a loosened matcher.

Both existing sets were imported by hand before this existed; the tests
assert this reproduces the manifest they produced.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import style_docs  # noqa: E402

PLATES = ROOT / "app" / "static" / "style-plates"
WIDTH = 1280
QUALITY = 82
EXTS = (".png", ".jpg", ".jpeg", ".webp")


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def match_style(token: str, styles: list[dict], aliases: dict) -> dict | None:
    """Exact normalised name, then a UNIQUE prefix. Never a fuzzy score —
    two styles that both start with the same word must be spelled out."""
    t = norm(aliases.get(token, token))
    exact = [st for st in styles if norm(st["name"]) == t]
    if exact:
        return exact[0]
    pref = [st for st in styles if norm(st["name"]).startswith(t)]
    return pref[0] if len(pref) == 1 else None


def plan(folder: pathlib.Path, library: str, aliases: dict) -> list[tuple]:
    styles = style_docs.styles(library)
    if not styles:
        raise SystemExit(f"{library} defines no styles — is its document there?")
    found, problems = [], []
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() not in EXTS:
            continue
        parts = f.stem.split("_")
        hit = None
        # Longest style token first: "Sci_Fi_Lived_In" is scene Sci_Fi,
        # style Lived_In — not scene Sci_Fi_Lived, style In.
        for cut in range(1, len(parts)):
            st = match_style("_".join(parts[cut:]), styles, aliases)
            if st:
                hit = ("_".join(parts[:cut]), st)
                break
        if hit is None:
            problems.append(f"{f.name}: no style in this library matches it")
            continue
        found.append((f, hit[0], hit[1]))
    if problems:
        raise SystemExit("refusing to guess:\n  " + "\n  ".join(problems))

    scenes = sorted({scene for _, scene, _ in found})
    if len(scenes) > 3:
        raise SystemExit(f"more than three scenes: {scenes}")
    slot = {s: i + 1 for i, s in enumerate(scenes)}

    claimed, out = {}, []
    for f, scene, st in found:
        cell = (st["key"], slot[scene])
        if cell in claimed:
            raise SystemExit(f"{st['name']} scene {scene} claimed twice: "
                             f"{f.name} and {claimed[cell]}")
        claimed[cell] = f.name
        out.append((f, st["key"], slot[scene]))

    missing = [f"{st['name']} ({3 - sum(1 for k, _ in claimed if k == st['key'])} short)"
               for st in styles
               if sum(1 for k, _ in claimed if k == st["key"]) != 3]
    if missing:
        print("INCOMPLETE — these styles will show fewer than three frames:")
        for m in missing:
            print("   ", m)
    return out


def run(library: str, folder: pathlib.Path, aliases: dict) -> dict:
    from PIL import Image
    jobs = plan(folder, library, aliases)
    PLATES.mkdir(parents=True, exist_ok=True)
    prefix = style_docs.LIBRARIES[library][1]
    for p in PLATES.glob(f"{prefix}*.webp"):   # this library's old frames only
        p.unlink()
    total = 0
    for src, key, slot in jobs:
        im = Image.open(src).convert("RGB")
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
        dest = PLATES / f"{key}-{slot}.webp"
        im.save(dest, "WEBP", quality=QUALITY, method=6)
        total += dest.stat().st_size

    index: dict[str, list[str]] = {}
    for p in sorted(PLATES.glob("*.webp")):
        key, slot = p.stem.rsplit("-", 1)
        index.setdefault(key, []).append(p.name)
    for k in index:
        index[k].sort()
    (PLATES / "index.json").write_text(json.dumps(index, indent=2) + "\n",
                                       encoding="utf-8")
    print(f"{len(jobs)} plates, {total / 1048576:.1f} MB")
    return index


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--alias")]
    aliases = {}
    for i, a in enumerate(sys.argv):
        if a == "--alias" and i + 1 < len(sys.argv):
            k, _, v = sys.argv[i + 1].partition("=")
            aliases[k] = v
    if len(args) < 2:
        raise SystemExit(__doc__)
    lib, folder = args[0], pathlib.Path(args[1])
    if lib not in style_docs.LIBRARIES:
        raise SystemExit(f"unknown library {lib!r} — "
                         f"one of {', '.join(style_docs.LIBRARIES)}")
    if not folder.is_dir():
        raise SystemExit(f"no such folder: {folder}")
    run(lib, folder, aliases)
