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

import copy
import json
import re
import shutil

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


# ------------------------------------------------------------- consolidation
# One breakdown, per-panel gates (user rulings 2026-08-16). Revisions were
# how a locked sheet got edited; a snapshot on each approved take answers
# "what was this approved AS?" better, so the chain is now a duplicate of
# itself. Collapsing is a migration, not an edit: it writes through the
# save_spec() gates deliberately, because those gates exist to stop a user
# rewriting history and this is the act that ENDS the history.
#
# Nothing is destroyed that a take needs. Candidate ids are allocated from
# one project-wide counter, so folding every revision's takes into the base
# directory cannot collide; each record keeps its own approval snapshot and
# gains consolidated_from, so provenance survives the id change.

def _spec_path(spec_id: str):
    return paths.SPECS_DIR / f"{paths.safe_id(spec_id)}.json"


def _board_dir(spec_id: str):
    return paths.BOARDS_DIR / paths.safe_id(spec_id)


def _takes_in(spec_id: str) -> list[dict]:
    d = _board_dir(spec_id)
    if not d.exists():
        return []
    out = []
    for p in sorted(d.glob("CAND-*.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return out


def consolidation_plan(base: str) -> dict:
    """What collapsing this unit would do, stated before it is done.

    The gate is readable as state: the caller renders this, not an error
    after the act."""
    from . import store
    base = base_of(base)
    revs = revisions_of(base)
    locks = store._load_locks()
    rows = []
    for rid in revs:
        takes = _takes_in(rid)
        rows.append({
            "spec_id": rid,
            "revision": revision_of(rid),
            "exists": _spec_path(rid).exists(),
            "locked": bool(locks.get(rid)),
            "takes": len(takes),
            "approved": sum(1 for r in takes if r.get("status") == "APPROVED"),
        })
    living = revs[-1] if revs else base
    return {
        "base": base,
        "revisions": rows,
        "content_from": living,
        "can_consolidate": len(revs) > 1,
        "why_not": "" if len(revs) > 1 else
                   f"{base} is already one breakdown.",
    }


def consolidate(base: str) -> dict:
    """Collapse a revision chain into one breakdown at the base id.

    The newest revision's document becomes the breakdown; older documents
    are archived INSIDE it (consolidated_from) rather than left as separate
    files, because a file on disk is a breakdown the user can open, and
    "I have two breakdowns" is the problem being solved. Every take moves
    to the base's directory and is retagged. A copy of every document
    touched is written to data/consolidations/ first."""
    from . import store
    base = base_of(base)
    revs = revisions_of(base)
    if len(revs) < 2:
        raise ValueError(f"{base} is already one breakdown — nothing to "
                         "consolidate.")
    living_id = revs[-1]
    living = store.get_spec(living_id)
    if not living:
        raise KeyError(living_id)

    # --- 1. a copy of everything, before anything moves
    stamp = "".join(c for c in store.utcnow() if c.isdigit())
    bak = paths.DATA / "consolidations" / f"{paths.safe_id(base)}-{stamp}"
    bak.mkdir(parents=True, exist_ok=True)
    for rid in revs:
        p = _spec_path(rid)
        if p.exists():
            shutil.copy2(p, bak / p.name)
    if paths.SPEC_LOCKS.exists():
        shutil.copy2(paths.SPEC_LOCKS, bak / "locks.json")

    # --- 2. one take pool. Collisions are checked across the whole chain
    #        before a single file moves — a half-folded board is worse than
    #        a refusal.
    dest = _board_dir(base)
    dest.mkdir(parents=True, exist_ok=True)
    pending = []
    for rid in revs:
        if rid == base:
            continue
        src = _board_dir(rid)
        if not src.exists():
            continue
        for f in sorted(src.iterdir()):
            if f.is_dir() or f.name == "keeps.json":
                continue
            if (dest / f.name).exists():
                raise FileExistsError(
                    f"{f.name} exists in both {rid} and {base} — refusing to "
                    "fold takes that would overwrite each other.")
            pending.append((rid, f))
    moved = []
    for rid, f in pending:
        shutil.move(str(f), str(dest / f.name))
        moved.append(f.name)

    retagged = []
    for meta in sorted(dest.glob("CAND-*.json")):
        try:
            rec = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        sid = str(rec.get("specification_id") or "")
        if sid and sid != base and base_of(sid) == base:
            rec["consolidated_from"] = sid
            rec["consolidated_at"] = store.utcnow()
            rec["specification_id"] = base
            store._atomic_write_json(meta, rec)
            retagged.append(rec.get("candidate_id"))

    # --- 3. one document. The older ones are archived inside it.
    locks = store._load_locks()
    history = list(living.get("consolidated_from") or [])
    for rid in revs:
        if rid == living_id:
            continue
        doc = store.get_spec(rid)
        if doc is None:
            continue
        history.append({"spec_id": rid, "revision": revision_of(rid),
                        "locked": bool(locks.get(rid)),
                        "archived_at": store.utcnow(),
                        "spec": copy.deepcopy(doc)})
    living = copy.deepcopy(living)
    living["specification_id"] = base
    living["revision"] = 1
    living["consolidated_from"] = history
    living["consolidated"] = {"at": store.utcnow(), "content_from": living_id,
                              "collapsed": list(revs)}

    from common import stable_hash  # scripts/common.py via paths sys.path hook
    prev = locks.get(living_id) or locks.get(base) or {}
    was_locked = bool(prev)
    store._atomic_write_json(_spec_path(base), living)

    # --- 4. the revisions stop existing as breakdowns
    for rid in revs:
        if rid == base:
            continue
        _spec_path(rid).unlink(missing_ok=True)
        locks.pop(rid, None)
        d = _board_dir(rid)
        if d.exists():
            keep = d / "keeps.json"
            if keep.exists() and not (dest / "keeps.json").exists():
                shutil.move(str(keep), str(dest / "keeps.json"))
            keep.unlink(missing_ok=True)
            try:
                d.rmdir()
            except OSError:
                pass  # something unexpected lives there; leave it visible
    if was_locked:
        locks[base] = {**prev, "hash": stable_hash(living),
                       "consolidated_at": living["consolidated"]["at"]}
    store._atomic_write_json(paths.SPEC_LOCKS, locks)

    gone = [r for r in revs if r != base]
    store.append_approval_log(
        f"BOARD {base}: CONSOLIDATED — {', '.join(gone)} collapsed into "
        f"{base}. Content taken from {living_id}; {len(moved)} take files "
        f"folded into one pool ({len(retagged)} retagged); older documents "
        f"archived inside the breakdown. Backup: {bak.name}. Revisions are "
        "retired — this breakdown is edited in place, gated per panel by "
        "its approved takes.")
    return {"base": base, "collapsed": gone, "content_from": living_id,
            "files_moved": len(moved), "takes_retagged": retagged,
            "locked": was_locked, "backup": str(bak)}


# A skip is the ONE case where deleting the revision machinery would change
# which takes a board uses, so it has to be reachable rather than only
# written to a log nothing reads (adversarial review F23: a boot with three
# collapses and one skip printed three lines and looked clean). Process-
# lived — boot fills it, the boot print and insights.blocking() read it. No
# skip has ever been recorded in the field; this is insurance against the
# take-id collision the docstring below names.
_SKIPPED: list[dict] = []


def skipped_migrations() -> list[dict]:
    return list(_SKIPPED)


def migrate_all_projects() -> list[dict]:
    """Collapse every legacy revision chain in every production, at boot.

    Revisions are retired (2026-08-16). Any `_R<n>` still on disk is legacy
    data, and leaving it there leaves the user with two breakdowns and two
    panel screens for one piece of work — the thing the retirement was
    supposed to end. So this is a MIGRATION, not an offer: no button, no
    modal, nothing to find. It runs once per chain and is naturally
    idempotent, because after it there is nothing left to collapse.

    Best-effort per project: one unmigratable chain (a take id colliding
    across revisions) must not take the boot down with it, and must not
    stop the next project migrating."""
    from . import store
    _SKIPPED.clear()          # this boot's skips, not the last one's
    out = []
    with paths.SWITCH_LOCK:
        prev = paths.ACTIVE_PROJECT
        try:
            for proj in paths.list_projects():
                paths.set_project(proj["slug"])
                if not paths.SPECS_DIR.exists():
                    continue
                bases = sorted({base_of(p.stem)
                                for p in paths.SPECS_DIR.glob("*.json")
                                if p.name != "locks.json"})
                for b in bases:
                    if len(revisions_of(b)) < 2:
                        continue
                    try:
                        r = consolidate(b)
                        r["project"] = proj["slug"]
                        out.append(r)
                    except Exception as e:  # noqa: BLE001 — boot must survive
                        _SKIPPED.append({"project": proj["slug"], "base": b,
                                         "reason": str(e)[:200]})
                        store.append_approval_log(
                            f"BOARD {b}: CONSOLIDATION SKIPPED — {e} "
                            "(the chain stays split; nothing was moved).")
        finally:
            paths.set_project(prev)
    return out
