"""Revision identity — one board per creative unit (user model, 2026-08-13).

A spec id and its `_R<n>` suffixed siblings are ONE unit; the board keys on
the BASE id. This module is the single home of that identity: parsing,
enumeration, the per-panel revision floor, the qualifying-approval map the
board reads, and the keeps registry.

Two rules everything here enforces:
- The base id IS R1's spec id, so `store.get_spec(base)` reads R1 — never
  "the unit". Anything board-shaped resolves through resolve_board_id()
  and takes its structure from newest_locked_revision().
- A draft revision never affects the board: floors and structure come from
  LOCKED revisions only.

Imports are lazy (paths only at module level) so store.py and generate.py
can import this module without a cycle.
"""
from __future__ import annotations

import json
import re

from . import paths

_REV_SUFFIX = re.compile(r"_R(\d+)$")


def base_of(spec_id: str) -> str:
    return _REV_SUFFIX.sub("", str(spec_id))


def revision_of(spec_id: str) -> int:
    m = _REV_SUFFIX.search(str(spec_id))
    return int(m.group(1)) if m else 1


def revisions_of(base: str) -> list[str]:
    """Every revision id of the unit, ordered oldest first. Anchored:
    CANYON_X must never swallow CANYON_XY_R2."""
    base = base_of(base)
    out = []
    if paths.SPECS_DIR.exists():
        pat = re.compile(re.escape(base) + r"(_R\d+)?$")
        for p in sorted(paths.SPECS_DIR.glob(f"{base}*.json")):
            if p.name == "locks.json":
                continue
            if pat.fullmatch(p.stem):
                out.append(p.stem)
    return sorted(out, key=revision_of)


def newest_locked_revision(base: str) -> str | None:
    """The revision that defines the unit's board structure. None while
    nothing is locked (the board has no structure yet)."""
    from . import store
    for rid in reversed(revisions_of(base)):
        if store.spec_locked(rid):
            return rid
    return None


def resolve_board_id(any_id: str) -> tuple[str, str | None]:
    """(base, structure_spec_id) for any spec/base id a board route gets."""
    base = base_of(any_id)
    return base, newest_locked_revision(base)


def panel_revision_floor(base: str, panel_id: str) -> int:
    """The revision at which this panel was last declared revised, walking
    LOCKED revisions newest-first. A locked revision without a stored
    revision_scope (legacy, pre-feature) counts as all-panels-revised —
    the honest reading: its board was a fork. Drafts never move the
    floor ("a draft revision never affects the board")."""
    from . import store
    for rid in reversed(revisions_of(base)):
        if not store.spec_locked(rid):
            continue
        spec = store.get_spec(rid) or {}
        scope = spec.get("revision_scope")
        if scope is None:
            if revision_of(rid) > 1:
                return revision_of(rid)
            return 1
        if panel_id in (scope.get("revised") or []):
            return revision_of(rid)
    return 1


# ------------------------------------------------------------ keeps registry

def _keeps_path(base: str):
    return paths.BOARDS_DIR / paths.safe_id(base_of(base)) / "keeps.json"


def load_keeps(base: str) -> dict:
    p = _keeps_path(base)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def set_keep(base: str, panel_id: str, candidate_id: str) -> dict:
    """The explicit act: seat a below-floor approved take on the board
    anyway. Validated (must exist, be APPROVED, and be below the panel's
    floor — keeping a qualifying take is a no-op) and journaled."""
    from . import generate, store
    base = base_of(base)
    rec = None
    for rid in revisions_of(base):
        rec = generate.get_candidate(rid, candidate_id)
        if rec is not None:
            break
    if rec is None:
        raise KeyError(candidate_id)
    if rec.get("status") != "APPROVED":
        raise ValueError(f"{candidate_id} is {rec.get('status')} — only an "
                         "APPROVED take can be kept.")
    if str(rec.get("panel_id")) != panel_id:
        raise ValueError(f"{candidate_id} is a {rec.get('panel_id')} take, "
                         f"not {panel_id}.")
    take_spec = str(rec.get("specification_id", ""))
    floor = panel_revision_floor(base, panel_id)
    if revision_of(take_spec) >= floor:
        raise ValueError(
            f"{candidate_id} already qualifies for {panel_id} — nothing to keep.")
    keeps = load_keeps(base)
    keeps[panel_id] = {"candidate_id": candidate_id, "spec_id": take_spec,
                       "from_revision": revision_of(take_spec),
                       "kept_at": store.utcnow()}
    store._atomic_write_json(_keeps_path(base), keeps)
    store.append_approval_log(
        f"BOARD {base} panel {panel_id}: KEPT {candidate_id} (approved "
        f"against {take_spec}, R{revision_of(take_spec)}) despite revision "
        f"floor R{floor} — explicit user act.")
    return keeps[panel_id]


def clear_keep(base: str, panel_id: str) -> dict:
    from . import store
    base = base_of(base)
    keeps = load_keeps(base)
    if panel_id not in keeps:
        raise KeyError(panel_id)
    gone = keeps.pop(panel_id)
    store._atomic_write_json(_keeps_path(base), keeps)
    store.append_approval_log(
        f"BOARD {base} panel {panel_id}: keep of {gone.get('candidate_id')} "
        "cleared — the slot asks again.")
    return {"panel_id": panel_id, "cleared": gone.get("candidate_id")}


# ------------------------------------------------------- qualifying approvals

def _cand_num(candidate_id: str) -> int:
    m = re.search(r"(\d+)$", str(candidate_id))
    return int(m.group(1)) if m else -1


def qualifying_approved_by_panel(base: str) -> dict:
    """The board's take pool, across every revision of the unit.

    qualifying: {panel_id: record} — APPROVED, CAND-prefixed, rendered
      against a revision >= the panel's floor (or the registered keep);
      newest candidate id wins (numeric tail — a padded counter must not
      break at width rollover).
    offered: {panel_id: [records…]} — approved but below the floor and not
      kept, newest first: the "approved against R(m) — re-render or keep"
      material.

    Records are shallow-copied and annotated take_spec_id / from_revision /
    kept (and kept_superseded on a keep outranked by a newer qualifying
    take — the keep was a bridge, not a pin)."""
    from . import generate
    base = base_of(base)
    keeps = load_keeps(base)
    floors: dict[str, int] = {}
    by_panel: dict[str, list[dict]] = {}

    for rid in revisions_of(base):
        for c in generate.list_candidates(rid):
            if c.get("status") != "APPROVED":
                continue
            if not str(c.get("candidate_id", "")).startswith("CAND-"):
                continue
            pid = str(c.get("panel_id", ""))
            if not pid:
                continue
            take_spec = str(c.get("specification_id") or rid)
            by_panel.setdefault(pid, []).append(
                {**c, "take_spec_id": take_spec,
                 "from_revision": revision_of(take_spec), "kept": False})

    qualifying: dict[str, dict] = {}
    offered: dict[str, list[dict]] = {}
    for pid, recs in by_panel.items():
        floor = floors.setdefault(pid, panel_revision_floor(base, pid))
        real = [r for r in recs if r["from_revision"] >= floor]
        below = [r for r in recs if r["from_revision"] < floor]
        kept_id = keeps.get(pid, {}).get("candidate_id")
        kept_rec = next((r for r in below
                         if r["candidate_id"] == kept_id), None)
        if real:
            # A genuinely qualifying take always outranks a kept bridge,
            # whatever their candidate numbers; among qualifiers, newest
            # candidate id wins.
            winner = max(real, key=lambda r: _cand_num(r["candidate_id"]))
            if kept_rec is not None:
                winner = {**winner, "kept_superseded": True}
            qualifying[pid] = winner
        elif kept_rec is not None:
            qualifying[pid] = {**kept_rec, "kept": True}
        # A keep whose take stopped being approved (or vanished) never
        # silently resurrects — kept_rec is simply absent and the panel
        # falls through to offered/NO_CANDIDATE verdicts.
        rest = [r for r in below if r is not kept_rec]
        if rest:
            offered[pid] = sorted(
                rest, key=lambda r: _cand_num(r["candidate_id"]),
                reverse=True)
    return {"qualifying": qualifying, "offered": offered}
