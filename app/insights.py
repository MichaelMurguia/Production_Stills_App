"""Derived project intelligence — read-only aggregation over existing stores.

Feeds the dashboard blocker list, stage summary, activity feed, reference
usage counts, screenplay location coverage, and the citation re-check. It
never writes canon data; the only file it owns is the citation report cache.
"""
from __future__ import annotations

import json
import re

from . import activity, generate, paths, store

def _citation_report_path():
    # Computed per call — paths.DATA moves with the active project.
    return paths.DATA / "citation_report.json"

STYLE_ANCHOR_ROLES = {"BOARD_LAYOUT_STYLE", "BOARD_RENDERING_STYLE",
                      "CINEMATOGRAPHY_STYLE"}


# ------------------------------------------------------------ evidence gaps

def evidence_gaps(spec: dict) -> list[dict]:
    """Required objects lacking a PASS evidence row — the exact rule approval
    enforces (scripts/validate_spec.py): every required object needs a PASS
    row with the same (panel_id, object) pair. HOLD, REMOVE, or no row at all
    are equally blocking."""
    passed = {(r.get("panel_id"), r.get("object"))
              for r in spec.get("evidence_ledger", [])
              if r.get("status") == "PASS"}
    return [{"panel_id": p.get("id"), "object": obj}
            for p in spec.get("panels", [])
            for obj in p.get("required_objects", [])
            if (p.get("id"), obj) not in passed]


# ------------------------------------------------------------------ blockers

def blocking() -> list[dict]:
    """Everything that stops the next render, as structured rows:
    kind HOLD (evidence), GAP (missing input), SIZE (undersized render),
    CITE (screenplay citation no longer found). Each row carries an `action`
    view hint so the UI can offer the resolving jump."""
    out: list[dict] = []
    app_state = store.load_app_state()
    refs = store.list_references()
    specs = store.list_specs()

    if not app_state.get("screenplay"):
        out.append({"kind": "GAP", "text": "Screenplay not uploaded",
                    "action": "dashboard"})
    if not any(r["role"] == "BOARD_LAYOUT_STYLE" and r["status"] == "APPROVED"
               for r in refs):
        out.append({"kind": "GAP",
                    "text": "Master Board #001 (BOARD_LAYOUT_STYLE) not "
                            "approved in reference library",
                    "action": "references"})

    approved_ref_ids = {r["id"] for r in refs if r["status"] == "APPROVED"}
    subjects = store.list_subjects()
    flagged_subjects: set[str] = set()

    for meta in specs:
        sid = meta["specification_id"]
        spec = store.get_spec(sid)
        if spec is None:
            continue

        if not meta["locked"] and meta["status"] != "REJECTED":
            gaps = evidence_gaps(spec)
            if gaps:
                first = gaps[0]
                out.append({
                    "kind": "HOLD", "spec_id": sid, "action": "specs",
                    "text": f"{len(gaps)} required object(s) lack PASS "
                            f"evidence — {sid}",
                    "detail": ", ".join(f"{g['panel_id']}/{g['object']}"
                                        for g in gaps[:4]),
                    "panel_id": first["panel_id"],
                })

        if meta["locked"]:
            # Subjects a locked sheet requires but no approved reference covers.
            for panel in spec.get("panels", []):
                for obj in panel.get("required_objects", []):
                    o = str(obj).casefold()
                    for subj in subjects:
                        name = subj.get("name", "").casefold()
                        if not name or subj.get("name") in flagged_subjects:
                            continue
                        if name in o and not (set(subj.get("ref_ids", []))
                                              & approved_ref_ids):
                            flagged_subjects.add(subj["name"])
                            out.append({
                                "kind": "GAP", "spec_id": sid,
                                "action": "wizard",
                                "text": f"No approved reference for "
                                        f"{subj['name']} — required by "
                                        f"{sid} {panel.get('id')}",
                            })

    # Undersized approved renders on locked sheets (never upscaled — 4b rule).
    from . import assemble
    for meta in specs:
        if not meta["locked"]:
            continue
        sid = meta["specification_id"]
        try:
            sm = assemble.slot_map(sid)
        except Exception:
            continue
        for slot in sm["slots"]:
            if slot["status"] == "TOO_SMALL":
                out.append({
                    "kind": "SIZE", "spec_id": sid, "action": "boards",
                    "panel_id": slot["panel_id"],
                    "text": f"Panel {slot['panel_id']} rendered "
                            f"{slot['candidate_width']}×{slot['candidate_height']}px "
                            f"into a {slot['slot_width']}×{slot['slot_height']}px "
                            f"slot — {sid} — never upscaled, regenerate larger",
                })

    rep = load_citation_report()
    if rep and rep.get("missing"):
        by_spec: dict[str, int] = {}
        for row in rep["missing"]:
            by_spec[row["spec_id"]] = by_spec.get(row["spec_id"], 0) + 1
        for sid, n in sorted(by_spec.items()):
            out.append({
                "kind": "CITE", "spec_id": sid, "action": "specs",
                "text": f"{n} cited quote(s) from {sid} no longer found in "
                        f"{rep.get('screenplay', 'the current screenplay')}",
            })

    # Backup reminder — advisory, always last so it never outranks real
    # blockers. Only projects with content deserve the nag.
    if app_state.get("screenplay") or specs:
        from . import backup
        days = backup.days_since_backup(paths.ACTIVE_PROJECT)
        if days is None:
            out.append({
                "kind": "CARE", "action": "projects",
                "text": "This production has never been backed up — download "
                        "a backup zip from Productions",
            })
        elif days >= 7:
            out.append({
                "kind": "CARE", "action": "projects",
                "text": f"Last backup {days} days ago — download a fresh one "
                        "from Productions",
            })
    return out


def _interview_answered() -> int:
    """How many look-interview fields hold answers — the gate chain's
    interview step tracks real state now that the interview persists."""
    p = paths.DATA / "interview.json"
    if not p.exists():
        return 0
    try:
        saved = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    return sum(1 for v in saved.values() if str(v).strip())


# --------------------------------------------------------------- stage summary

def stage_summary(blockers: list[dict] | None = None) -> dict:
    """Per-stage status for the pipeline band and next-verb logic. Pure
    aggregation — every number is derivable by clicking around the app."""
    app_state = store.load_app_state()
    refs = store.list_references()
    specs = store.list_specs()

    anchors = sum(1 for r in refs if r["status"] == "APPROVED"
                  and store.role_head(r["role"]) in STYLE_ANCHOR_ROLES)
    locked = [s for s in specs if s["locked"]]
    drafts = [s for s in specs if not s["locked"] and s["status"] != "REJECTED"]
    if blockers is None:
        blockers = blocking()
    blocked_sheets = {b["spec_id"] for b in blockers
                     if b["kind"] == "HOLD" and b.get("spec_id")}

    cand_total = cand_approved = 0
    boards_total = boards_approved = 0
    for s in specs:
        sid = s["specification_id"]
        for c in generate.list_candidates(sid):
            cand_total += 1
            if c.get("status") == "APPROVED":
                cand_approved += 1
        d = paths.BOARDS_DIR / sid
        for p in (d.glob("BOARD-*.json") if d.exists() else []):
            boards_total += 1
            try:
                if json.loads(p.read_text(encoding="utf-8")).get("status") == "APPROVED":
                    boards_approved += 1
            except json.JSONDecodeError:
                continue

    return {
        "screenplay": app_state.get("screenplay") or None,
        "production_design": {
            "bible_saved": paths.BIBLE.exists(),
            "bible_rev": int(app_state.get("bible_rev", 0)),
            # The Script Scene Scan has run (LOCKED_STAGE_PLAN L3) — feeds
            # the gate chain so its step drops off when done.
            "scan_done": paths.WIZARD_ANALYSIS.exists(),
            "interview_answered": _interview_answered(),
            "style_anchors": anchors,
            "subjects": len(store.list_subjects()),
            "lessons": len(generate.load_lessons()),
        },
        "breakdowns": {
            "locked": len(locked),
            "drafts": len(drafts),
            "blocked": len(blocked_sheets),
        },
        "panels": {"approved": cand_approved, "candidates": cand_total},
        "boards": {"assembled": boards_total, "approved": boards_approved},
    }


def next_verb(summary: dict, blockers: list[dict]) -> dict:
    """The single next action when nothing is blocking — a screen with no
    verb is not finished (DESIGN_SYSTEM copy rule). Advisory rows (CARE)
    are never promoted to the lead (design review 2026-08-01 §9)."""
    blockers = [b for b in blockers if b.get("kind") != "CARE"]
    if blockers:
        b = blockers[0]
        return {"text": b["text"], "action": b.get("action", "dashboard")}
    if not summary["screenplay"]:
        return {"text": "Upload the screenplay", "action": "dashboard"}
    if not summary["production_design"]["bible_saved"]:
        return {"text": "Draft the Art Direction Bible in the setup wizard",
                "action": "wizard"}
    if summary["breakdowns"]["locked"] == 0:
        if summary["breakdowns"]["drafts"] == 0:
            return {"text": "Draft a breakdown sheet from the screenplay",
                    "action": "specs"}
        return {"text": "Validate and lock a draft breakdown sheet",
                "action": "specs"}
    if summary["panels"]["approved"] == 0:
        return {"text": "Generate and approve panels for a locked sheet",
                "action": "boards"}
    if summary["boards"]["assembled"] == 0:
        return {"text": "Assemble the first 4K board", "action": "boards"}
    return {"text": "Generate panels for the next sheet, or assemble a board",
            "action": "boards"}


# -------------------------------------------------------------- activity feed

def _seg(path: str, i: int) -> str:
    parts = path.strip("/").split("/")
    return parts[i] if len(parts) > i else ""


def _friendly_event(e: dict) -> dict | None:
    p = e.get("path", "")
    m = e.get("method", "")
    body = e.get("body") or {}
    status = int(e.get("status", 0))
    if not isinstance(body, dict):
        body = {}
    if p.startswith("/api/settings"):
        return None  # keys and preferences are not project history

    if status >= 400:
        detail = str(e.get("error", ""))[:120]
        return {"ts": e.get("ts", ""), "kind": "error",
                "text": f"{m} {p} failed ({status})"
                        + (f" — {detail}" if detail else "")}

    sid, cid, pid = _seg(p, 2), "", ""
    if "/candidates/" in p:
        cid = _seg(p, 4)
    if "/panels/" in p:
        pid = _seg(p, 4)

    if p.endswith("/generate"):
        prov = body.get("provider") or ""
        size = body.get("image_size") or ""
        extra = " · ".join(x for x in [prov, size] if x)
        return {"ts": e["ts"], "kind": "ok",
                "text": f"Generated a candidate for {sid} {pid}"
                        + (f" ({extra})" if extra else "")}
    if p.endswith("/repair"):
        prov = body.get("provider") or ""
        return {"ts": e["ts"], "kind": "ok",
                "text": f"Region repair from {cid} on {sid}"
                        + (f" ({prov})" if prov else "")}
    if p.endswith("/rerender"):
        return {"ts": e["ts"], "kind": "ok",
                "text": f"Full-resolution re-render of {cid} on {sid} "
                        f"({body.get('provider', '')}/{body.get('image_size', '')})"}
    if p.endswith("/status") and cid:
        st = str(body.get("status", "")).upper()
        reason = str(body.get("reason", "")).strip()
        if st == "REJECTED":
            return {"ts": e["ts"], "kind": "ok",
                    "text": f"Rejected {cid}" + (f" — {reason}" if reason else "")}
        if st == "APPROVED":
            return {"ts": e["ts"], "kind": "ok", "text": f"Approved {cid}"}
        return None
    if p.endswith("/status") and "/references/" in p:
        st = str(body.get("status", "")).title()
        return {"ts": e["ts"], "kind": "ok",
                "text": f"{st} reference {_seg(p, 2)}"}
    if m == "DELETE" and cid:
        return {"ts": e["ts"], "kind": "ok", "text": f"Deleted {cid} permanently"}
    if p.endswith("/purge-rejected"):
        return {"ts": e["ts"], "kind": "ok",
                "text": f"Purged rejected candidates on {sid}"}
    if p.endswith("/approve") and sid:
        return {"ts": e["ts"], "kind": "ok", "text": f"Locked {sid}"}
    if p.endswith("/unlock"):
        return {"ts": e["ts"], "kind": "ok",
                "text": f"Unlocked {sid} — back to draft"}
    if p.endswith("/revise"):
        return {"ts": e["ts"], "kind": "ok", "text": f"Created a revision of {sid}"}
    if p.endswith("/assemble"):
        return {"ts": e["ts"], "kind": "ok", "text": f"Assembled a 4K board for {sid}"}
    if p.endswith("/promote"):
        return {"ts": e["ts"], "kind": "ok",
                "text": f"Promoted {cid} into the reference library"}
    if p.endswith("/lighting-study"):
        return {"ts": e["ts"], "kind": "ok",
                "text": f"Derived a lighting study from {cid}"}
    if "/derive/" in p:
        what = _seg(p, 4)
        return {"ts": e["ts"], "kind": "ok", "text": f"Derived {what} for {sid}"}
    if p == "/api/screenplay" and m == "POST":
        return {"ts": e["ts"], "kind": "ok", "text": "Uploaded a screenplay draft"}
    if p == "/api/style-bible" and m == "PUT":
        return {"ts": e["ts"], "kind": "ok", "text": "Saved the Art Direction Bible"}
    if p == "/api/wizard/analyze":
        return {"ts": e["ts"], "kind": "ok", "text": "Ran screenplay analysis"}
    if p == "/api/specs/autofill":
        drafted = str(body.get("specification_id", "")).strip()
        return {"ts": e["ts"], "kind": "ok",
                "text": f"Drafted breakdown {drafted}" if drafted
                        else "Drafted a breakdown sheet"}
    if p == "/api/references" and m == "POST":
        return {"ts": e["ts"], "kind": "ok", "text": "Added a reference image"}
    return None


def recent_activity(limit: int = 10) -> list[dict]:
    if not activity._log_path().exists():
        return []
    lines = activity._log_path().read_text(encoding="utf-8").splitlines()[-500:]
    events: list[dict] = []
    for ln in reversed(lines):
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        ev = _friendly_event(e)
        if ev:
            events.append(ev)
        if len(events) >= limit:
            break
    return events


# ----------------------------------------------------------- reference usage

def reference_usage() -> dict[str, int]:
    """How many renders each reference has anchored — candidate records
    already carry their attached reference IDs."""
    counts: dict[str, int] = {}
    for meta in store.list_specs():
        for c in generate.list_candidates(meta["specification_id"]):
            for r in c.get("references", []):
                rid = r.get("id")
                if rid:
                    counts[rid] = counts.get(rid, 0) + 1
    return counts


# ------------------------------------------------------- screenplay coverage

_text_cache: dict[str, str] = {}

_SLUG_RE = re.compile(r"^(INT\.?/EXT\.?|EXT\.?/INT\.?|I/E|INT|EXT)[.\s]+(.+)$")

# Trailing time-of-day / continuity markers that PDF extraction often glues
# onto the location when the " - " separator is lost.
_TIME_TAIL = {"DAY", "NIGHT", "DAWN", "DUSK", "MORNING", "AFTERNOON",
              "EVENING", "LATER", "CONTINUOUS", "SAME", "MOMENTS",
              "SUNSET", "SUNRISE", "NIGHTFALL", "TIME", "PRESENT"}


def _strip_time_tail(place: str) -> str:
    words = place.split()
    while len(words) > 1 and words[-1].strip(".,") in _TIME_TAIL:
        words.pop()
    return " ".join(words)


def screenplay_text() -> str:
    rec = store.load_app_state().get("screenplay")
    if not rec:
        return ""
    p = paths.SCREENPLAY_DIR / rec["file"]
    if not p.exists():
        return ""
    key = rec.get("sha256") or rec["file"]
    if key in _text_cache:
        return _text_cache[key]
    if p.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            text = "\n".join((page.extract_text() or "")
                             for page in PdfReader(str(p)).pages)
        except Exception:
            text = ""
    else:
        text = p.read_bytes().decode("utf-8", "replace")
    _text_cache.clear()  # only ever one current screenplay
    _text_cache[key] = text
    return text


_KW_STOPWORDS = frozenset("""the and for with that this from into their there
then than have has had was were are is be been being not but they them she her
his him hers its itself out off over under about after before while when where
what who whom which why how all any both each few more most other some such
only own same very can could will would just don should now you your yours our
ours we us as at by in of on to up an a or if do does did so no nor too again
once here down further against between through during above below because
until unless around toward towards onto upon like one two three back looks
looking look looked sees see seen comes come came goes go went gets get got
takes take took turns turn turned pulls pull pulled moves move moved still
away behind toward front inside outside something nothing everything someone
everyone another away then there day night morning evening dawn dusk moment
beat int ext cut angle close pov scene continued cont sfx vfx voice
continuous""".split())


def derive_keywords(name: str, limit: int = 20) -> dict:
    """Deterministic trigger-word derivation for a design language: find
    every mention of the name's words in the screenplay and rank the
    vocabulary that travels with them (±12-word windows, stopwords and
    screenplay furniture dropped, must recur). No model — same contract as
    the slugline parse. The name's own words lead the list; the UI leaves
    the result editable before anything is saved."""
    text = screenplay_text()
    if not text.strip():
        return {"available": False, "hits": 0, "keywords": []}
    name_tokens = [w for w in re.findall(r"[a-z0-9]+", name.lower())
                   if len(w) >= 3 and w not in _KW_STOPWORDS]
    if not name_tokens:
        return {"available": True, "hits": 0, "keywords": []}
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    wanted = set(name_tokens)
    hits = [i for i, t in enumerate(tokens) if t in wanted]
    from collections import Counter
    near = Counter()
    for i in hits:
        for t in tokens[max(0, i - 12): i + 13]:
            if len(t) >= 3 and not t.isdigit() \
                    and t not in _KW_STOPWORDS and t not in wanted:
                near[t] += 1
    ranked = [w for w, c in near.most_common() if c >= 2]
    return {"available": True, "hits": len(hits),
            "keywords": (name_tokens + ranked)[:limit]}


def locations() -> dict:
    """Slugline coverage map: every location the screenplay names, scene
    count, and a stated detail heuristic (non-empty lines inside its scenes —
    thin coverage means a breakdown leans on budgeted inference). Deterministic
    parse; no model involved."""
    text = screenplay_text()
    if not text.strip():
        rec = store.load_app_state().get("screenplay")
        reason = ("no screenplay uploaded" if not rec else
                  "screenplay text could not be extracted (image-only PDF?)")
        return {"available": False, "reason": reason, "locations": []}

    lines = text.splitlines()
    scenes: list[dict] = []
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s or len(s) > 90 or s != s.upper():
            continue
        m = _SLUG_RE.match(s)
        if not m:
            continue
        place = re.split(r"\s+[-–—]\s+", m.group(2))[0].strip(" .-–—")
        place = _strip_time_tail(place)
        if not place:
            continue
        scenes.append({"line": i, "heading": s,
                       "int_ext": m.group(1).replace(".", "").upper(),
                       "location": place})
    for idx, sc in enumerate(scenes):
        end = scenes[idx + 1]["line"] if idx + 1 < len(scenes) else len(lines)
        sc["body"] = sum(1 for l in lines[sc["line"] + 1:end] if l.strip())

    groups: dict[str, dict] = {}
    for sc in scenes:
        g = groups.setdefault(sc["location"], {
            "location": sc["location"], "int_ext": set(),
            "scenes": 0, "body_lines": 0, "scene_list": []})
        g["int_ext"].add(sc["int_ext"])
        g["scenes"] += 1
        g["body_lines"] += sc["body"]
        g["scene_list"].append({"heading": sc["heading"], "line": sc["line"]})

    # Sheet match: a spec covers a location when either name contains the
    # other (apostrophes/dashes folded — PDFs and specs disagree on curly
    # quotes).
    sheets = []
    for meta in store.list_specs():
        spec = store.get_spec(meta["specification_id"])
        if spec is None:
            continue
        loc = str((spec.get("setting") or {}).get("location", "")).strip()
        sheets.append({"spec_id": meta["specification_id"], "loc": _norm(loc),
                       "subject": _norm(str(spec.get("subject", ""))),
                       "status": meta["status"], "locked": meta["locked"]})

    def word_in(needle: str, hay: str) -> bool:
        # Whole-word containment — "shop" must not match "workshop".
        return bool(needle) and bool(
            re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", hay))

    out = []
    for g in sorted(groups.values(), key=lambda x: -x["scenes"]):
        lc = _norm(g["location"])
        match = next((s for s in sheets if s["loc"] and
                      (word_in(s["loc"], lc) or word_in(lc, s["loc"]))), None)
        if match is None:
            match = next((s for s in sheets if word_in(lc, s["subject"])), None)
        detail = (1 if g["body_lines"] < 10 else
                  2 if g["body_lines"] < 30 else
                  3 if g["body_lines"] < 80 else 4)
        out.append({
            "location": g["location"],
            "int_ext": "/".join(sorted(g["int_ext"])),
            "scenes": g["scenes"],
            "body_lines": g["body_lines"],
            "detail": detail,
            "scene_list": g["scene_list"],
            "sheet": ({"spec_id": match["spec_id"], "locked": match["locked"],
                       "status": match["status"]} if match else None),
        })
    return {"available": True, "locations": out,
            "scene_count": len(scenes)}


# ------------------------------------------------------------ citation check

def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = re.sub(r"[—–−]", "-", s)  # PDF extraction folds em-dashes to hyphens
    return re.sub(r"\s+", " ", s).casefold().strip()


def _squash(s: str) -> str:
    """Letters and digits only — the last-resort comparison. PDF text
    extraction mangles spacing, dashes, and line breaks; a citation only
    counts as missing when even its bare letters are gone."""
    return re.sub(r"[^a-z0-9]", "", s.casefold())


_QUOTE_RE = re.compile(r'["“]([^"“”]{12,300})["”]')


def citation_check() -> dict:
    """Re-search every quoted evidence citation in the current screenplay
    text. Rows whose quotes vanish are REPORTED, never auto-mutated — locked
    sheets are immutable by canon rule; the director decides what a broken
    citation means."""
    text = _norm(screenplay_text())
    rec = store.load_app_state().get("screenplay") or {}
    if not text:
        report = {"checked_at": store.utcnow(),
                  "screenplay": rec.get("file", ""),
                  "available": False, "quotes_checked": 0, "missing": []}
        _save_citation_report(report)
        return report

    squashed = _squash(text)
    checked = 0
    missing = []
    for meta in store.list_specs():
        sid = meta["specification_id"]
        spec = store.get_spec(sid)
        if spec is None:
            continue
        for row in spec.get("evidence_ledger", []):
            for quote in _QUOTE_RE.findall(str(row.get("source", ""))):
                checked += 1
                if _norm(quote) not in text and _squash(quote) not in squashed:
                    missing.append({
                        "spec_id": sid,
                        "object_id": row.get("object_id", ""),
                        "panel_id": row.get("panel_id", ""),
                        "object": row.get("object", ""),
                        "quote": quote,
                        "locked": meta["locked"],
                    })
    report = {"checked_at": store.utcnow(), "screenplay": rec.get("file", ""),
              "available": True, "quotes_checked": checked, "missing": missing}
    _save_citation_report(report)
    return report


def _save_citation_report(report: dict) -> None:
    _citation_report_path().write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8")


def load_citation_report() -> dict | None:
    if not _citation_report_path().exists():
        return None
    try:
        return json.loads(_citation_report_path().read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
