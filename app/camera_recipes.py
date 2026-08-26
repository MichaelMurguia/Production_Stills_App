"""A2 — the framing a panel is rendered at, chosen once and readable.

Two days of renders came back flat under a Subjective/Poetic grammar
while every part of the plumbing tested correct. The grammar said
`selective focus`, `negative space`, `unusual subject placement` — and an
image model satisfies all three by doing nothing, because an
everything-sharp frame contains selective focus if the model decides it
does. There was never a lens, an aperture or a focus plane in the prompt
at all; only a production-wide default nobody chose.

A framing row cannot be satisfied by doing nothing. `50–100mm, f/1.4–2.8,
selective` has one reading.

The choice is made at BREAKDOWN time and stored on the panel, not
resolved at compile time, and that is the part to hold onto. Deciding it
during compile would repeat the failure this whole week was made of: a
decision the app makes invisibly, inferable only from the picture. On the
panel it is inspectable before the spend, arguable, editable, recorded on
the take, and paid for once.

Resolution, four states, the same shape the grammar already uses:

    panel says NONE      → no framing; the manual camera axes alone
    panel names a row    → that row
    panel says nothing   → the grammar's first sanctioned row
    no grammar at all    → nothing, and renders are byte-identical to
                           before, which is what makes this reversible
"""
from __future__ import annotations

from . import style_docs

PANEL_FIELD = "camera_recipe"
MODS_FIELD = "camera_recipe_mods"
PANEL_NONE = "NONE"


def recipes() -> list[dict]:
    return style_docs.camera_recipes()


def by_key(key: str) -> dict | None:
    return style_docs.camera_recipe(key)


def axes() -> list[dict]:
    return style_docs.modifier_axes()


def sanctioned(panel: dict | None = None) -> list[dict]:
    """The rows this panel's grammar sanctions, its default first.

    A grammar constrains the FAMILY without determining the row — an
    action beat under Subjective/Poetic is `subjective-poetic-character`
    or `immersive-inside-the-action` opened up, never
    `epic-environmental-wide`. With no grammar, every row is available:
    a production that has not chosen a grammar has not narrowed anything,
    and offering it five rows out of twenty would be inventing a rule.
    """
    from . import cinematography as _cine
    st = _cine.resolve(panel)
    ids = (st or {}).get("recipes") or []
    if not ids:
        return recipes()
    known = {r["key"]: r for r in recipes()}
    return [known[i] for i in ids if i in known]


def panel_choice(panel: dict | None) -> str:
    """What this panel says: "" inherit, "NONE" refuse, or a row ID.

    Unrecognised inherits. An unknown ID must not silently delete the
    framing from one render — that is the invisible-decision failure in
    miniature."""
    v = str((panel or {}).get(PANEL_FIELD) or "").strip()
    if not v:
        return ""
    if v.upper() == PANEL_NONE:
        return PANEL_NONE
    return v if by_key(v) else ""


def resolve(panel: dict | None = None) -> dict | None:
    """The framing row this panel actually renders at."""
    pick = panel_choice(panel)
    if pick == PANEL_NONE:
        return None
    if pick:
        return by_key(pick)
    from . import cinematography as _cine
    st = _cine.resolve(panel)
    ids = (st or {}).get("recipes") or []
    return by_key(ids[0]) if ids else None


def mods(panel: dict | None = None) -> list[dict]:
    """The modifier deltas set on this panel, as {axis, name, setting}.

    Deltas only, and only where the shot departs from the row's baseline,
    so a prompt carries the difference rather than restating the row it
    already named. An axis or setting the document no longer defines is
    dropped: the document is the source of truth, and a stale delta would
    ride a prompt describing a camera move nobody can find."""
    raw = (panel or {}).get(MODS_FIELD) or {}
    if not isinstance(raw, dict):
        return []
    out = []
    for ax in axes():
        v = str(raw.get(ax["key"]) or "").strip()
        if not v:
            continue
        hit = next((s for s in ax["settings"] if s["setting"] == v), None)
        if hit:
            out.append({"axis": ax["key"], "name": ax["name"],
                        "setting": hit["setting"], "effect": hit["effect"]})
    return out


def lines(panel: dict | None = None) -> list[str]:
    """The framing as prompt lines, for the top of the CAMERA block.

    Not its own block. The recipe IS the camera, and giving it a separate
    heading would put two camera authorities in one prompt — which is the
    contradiction that made a 19,094-character prompt render worse than a
    1,782-character one."""
    r = resolve(panel)
    if not r:
        return []
    out = [f"- FRAMING — {r['value']}."]
    for m in mods(panel):
        out.append(f"- {m['name'].upper()} — {m['setting']}: {m['effect'].rstrip('.')}.")
    return out


LINE_HEAD = "- FRAMING —"


def stamp(panel: dict | None = None, sent: str = "") -> dict:
    """What a take records about the framing it rode.

    `sent` is the text the image model was actually given. Pass it.

    C4 was about reading `prompt` when `render_prompt` was the truth, and
    this is the same mistake one level up: a stamp built from the panel's
    CURRENT fields reports what the app intends, not what it sent. Those
    differ whenever a saved prompt is in force, because the CAMERA block
    is deliberately not one of the blocks refreshed into a saved prompt —
    it is the panel's own wording, which is the right rule and makes the
    stamp a liar without this check.

    Caught by the user on CAND-0035 (2026-08-26): the badge read
    `FRAMING — SUBJECTIVE / POETIC CHARACTER · 50-100mm, f/1.4-2.8,
    SELECTIVE` over a deep-focus wide of a ship on a salt pan. The panel
    did resolve that framing. The prompt that rendered it was saved before
    framings existed and still said 24mm, wide, deep — and the image is
    exactly what it asked for. The record was the only thing that was
    wrong.
    """
    r = resolve(panel)
    pick = panel_choice(panel)
    if r and sent and LINE_HEAD not in sent:
        # It resolves, and it did not ride. Both facts, because "no
        # framing" alone would read as a panel that never chose one.
        return {"rides": False, "refused": False, "in_prompt": False,
                "would_be": r["key"], "would_be_name": r["name"],
                "why": "the prompt this take was rendered from carries its "
                       "own CAMERA block, saved before this framing was set"}
    if not r:
        return {"rides": False, "refused": pick == PANEL_NONE}
    return {"rides": True, "key": r["key"], "name": r["name"],
            "focal": r["focal"], "aperture": r["aperture"], "focus": r["focus"],
            "from": "panel" if pick else "grammar",
            "mods": [{"axis": m["axis"], "setting": m["setting"]}
                     for m in mods(panel)]}


WHY_FIELD = "camera_recipe_why"


def conflict(panel: dict | None = None) -> str:
    """A3.3 — a panel whose framing fights its own grammar, said plainly.

    Not silently resolved, and not refused either. The research pass is
    only offered rows its grammar sanctions, so this arises the other way
    round: someone chooses a framing and then changes the grammar under
    it, or overrides the grammar on one panel. Both are legitimate — a
    director wanting an epic environmental wide under a subjective grammar
    is making a choice, not a mistake.

    What is NOT legitimate is the app knowing the two disagree and saying
    nothing, which is how a production-wide 24mm sat under a
    selective-focus grammar for two days.
    """
    r = resolve(panel)
    if not r:
        return ""
    from . import cinematography as _cine
    st = _cine.resolve(panel)
    ids = (st or {}).get("recipes") or []
    if not ids or r["key"] in ids:
        return ""
    return (f"{r['name']} is not a framing {st['name']} sanctions. "
            f"That grammar's own rows are "
            + ", ".join((by_key(i) or {}).get("name", i) for i in ids[:3])
            + ". Rendering it is a choice, not an error — but the two "
              "will pull against each other.")
