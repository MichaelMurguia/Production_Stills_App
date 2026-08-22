"""The cinematography grammars, read from `docs/CINEMATOGRAPHY_STYLES.md`.

User ruling 2026-08-16: the eight styles in that document replace the
seven light-behaviour looks the picker shipped with. They are parsed, not
copied — the document is the source of truth and the one the user
maintains, so editing it updates the app and there is never a second list
to keep in step. A style the document drops disappears from the picker;
a style it gains appears there.

What the card shows comes straight from the document's own headings:
title and subtitle from the `# n. Name — Subtitle` line, then Key
Question, Description, Operating Principle, and — behind a link, because
it runs to a page — the Image-Model Prompt.

`value` is what actually rides a render, and it is deliberately NOT the
full prompt: the document's own Usage Note says generation should rely on
the visual mechanics and operating principle rather than asking a model
to imitate a named film. So the directive is the style, its principle and
its mechanics; the reference films stay human-facing context.
"""
from __future__ import annotations

import re

from . import paths

# The parser moved to style_docs on 2026-08-22, when world texture and
# rendering style became document-backed too. Three libraries, one
# implementation — a second copy of this parse is how the picker and the
# document drift apart, which is the exact failure the 2026-08-16 ruling
# was written to prevent.
from . import style_docs

LIB = "cinematography"


def _doc_path():
    return style_docs.doc_path(LIB)


def slug(name: str) -> str:
    return style_docs.slug(LIB, name)


def styles() -> list[dict]:
    """The eight grammars this document defines. See style_docs."""
    return style_docs.styles(LIB)


# ----------------------------------------------- the grammar that rides

SETTING_KEY = "cinematography"


def setting() -> dict:
    """The production's DEFAULT grammar. Stored per production.

    There was a second field here, `prompt_rides` — an off-by-default
    switch controlling whether the grammar's image-model prompt reached a
    render at all. It existed so the 2026-08-16 addition could be
    evaluated and rolled back, and it earned its keep for that.

    Retired 2026-08-22 by the user, who had done the evaluating: "there
    should be no switch on the panels in the Production Design tab. That
    sets the default. It should be over-rideable on the panel render tab."
    So the model is two levers, not three — a production default, and a
    per-panel override that can name another grammar or refuse one with
    NONE. A stored `prompt_rides` from before is simply ignored; there is
    nothing to migrate, because the value it held is no longer a
    question anyone is asked."""
    from . import store
    # Under paths.SWITCH_LOCK, the same lock next_counter() uses. A render
    # compiles its prompt while other renders are allocating candidate
    # ids, and on Windows an unlocked read of app_state while another
    # thread os.replace()s it raises PermissionError — ten concurrent
    # renders found this immediately.
    with paths.SWITCH_LOCK:
        raw = store.load_app_state().get(SETTING_KEY) or {}
    return {"key": str(raw.get("key", ""))}


def save_setting(key: str = None) -> dict:
    from . import store
    cur = setting()
    if key is not None:
        cur["key"] = str(key)
    with paths.SWITCH_LOCK:
        state = store.load_app_state()
        state[SETTING_KEY] = cur
        store.save_app_state(state)
    store.append_approval_log(
        f"CINEMATOGRAPHY: production default grammar = {cur['key'] or 'none'}. "
        "Every panel renders under it unless the panel names another or "
        "refuses one.")
    return cur


def by_key(key: str) -> dict | None:
    for st in styles():
        if st["key"] == key:
            return st
    return None


def active() -> dict | None:
    """The production's default grammar, or None if it has not chosen one."""
    key = setting()["key"]
    return by_key(key) if key else None


PANEL_FIELD = "cinematography"
PANEL_NONE = "NONE"


def panel_choice(panel: dict | None) -> str:
    """What this panel says about grammar: "" inherit, "NONE" refuse, or a
    style key. Anything unrecognised inherits — an unknown value must not
    silently delete a production's grammar from one render."""
    v = str((panel or {}).get(PANEL_FIELD) or "").strip()
    if not v:
        return ""
    if v.upper() == PANEL_NONE:
        return PANEL_NONE
    return v if any(st["key"] == v for st in styles()) else ""


def resolve(panel: dict | None = None) -> dict | None:
    """The grammar this panel actually renders under.

    Three states, the same shape every camera axis already uses: unset
    inherits the production's choice, a key overrides it, and NONE refuses
    it for this panel alone (user, 2026-08-22).

    A panel that names a grammar rides it even when the production switch
    is off. The switch governs the DEFAULT — "add it to every render" —
    and a panel naming a grammar is asking for it on that panel; if the
    switch still suppressed it, choosing per panel would do nothing at all.
    NONE is the inverse and wins over a switch that is on.
    """
    pick = panel_choice(panel)
    if pick == PANEL_NONE:
        return None
    if pick:
        return next((st for st in styles() if st["key"] == pick), None)
    return active()


def prompt_block(panel: dict | None = None) -> list[str]:
    """The document's own image-model prompt, verbatim, as a render block.

    Placed AFTER the camera block and explicitly subordinate to it on
    framing: the grammar says "favour moderate wide-angle" and a panel may
    say 85mm, and the panel's camera is the one the user set on purpose.
    Same precedence the CAMERA block already claims over references."""
    st = resolve(panel)
    if not st:
        return []
    scope = ("This panel names this grammar itself."
             if panel_choice(panel) else
             "This is the production's visual grammar and applies to every "
             "panel.")
    return [f"CINEMATOGRAPHY GRAMMAR — {st['name'].upper()} ({st['subtitle']}). "
            + scope +
            " Where it suggests a framing, lens or angle that the "
            "CAMERA block above states explicitly, the CAMERA block wins — "
            "this grammar governs approach, not the shot.",
            "", st["prompt"], ""]


def stamp(panel: dict | None = None) -> dict:
    """What a take records about the grammar it was rendered under, so a
    take made with it can be told from one made without."""
    from common import stable_hash
    st = resolve(panel)
    pick = panel_choice(panel)
    if not st:
        # A panel that refused says so — otherwise a take made under NONE
        # is indistinguishable from one made before the grammar existed.
        return {"rides": False, "refused": pick == PANEL_NONE}
    return {"rides": True, "key": st["key"], "name": st["name"],
            "from": "panel" if pick else "production",
            "prompt_sha": stable_hash(st["prompt"])[:16]}
