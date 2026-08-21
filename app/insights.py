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

# The Production Design shelf (four-anchor ruling 2026-08-03): three movie
# parameters + one board parameter. BOARD_LAYOUT_STYLE is assembly grammar
# and counts toward Boards, not Production Design.
STYLE_ANCHOR_ROLES = {"WORLD_TEXTURE", "COLOR_PALETTE",
                      "CINEMATOGRAPHY_STYLE", "BOARD_RENDERING_STYLE"}


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
    kind HOLD (evidence), GAP (missing input), KEY (no usable credential
    for an AI role), SIZE (undersized render), CITE (screenplay citation
    no longer found). Each row carries an `action` view hint so the UI can
    offer the resolving jump, and may carry a `stage` hint naming the
    pipeline stage it blocks when that is not derivable from `action`."""
    out: list[dict] = []
    app_state = store.load_app_state()
    refs = store.list_references()
    specs = store.list_specs()

    # A missing credential is a blocker (user ruling 2026-08-18; shape
    # ruled by TRIAGE_PLAN §2, 2026-08-18). ONE row per missing
    # credential, never one per stage — there is one thing to fix. The
    # row names the SHAPE of the loss; the stage line beneath it carries
    # the precision, which is how "the two roles fail separately" reads
    # without a second row. `scope: install` because this is the only
    # blocker whose truth survives a production switch, and a reader who
    # fixes it once must never see it filed as this production's fault.
    cap = generate.capability()
    narr, img = cap["narrative"], cap["image"]
    if not (narr["usable"] and img["usable"]):
        both = not narr["usable"] and not img["usable"]
        stages = ([] + (["wizard"] if not narr["usable"] else [])
                  + (["boards"] if not img["usable"] else []))
        if both:
            text = ("Every engine key failed its last test — nothing can be "
                    "read, drafted or rendered") if (narr["failed"] and img["failed"])                 else "No AI engine connected — nothing can be read, drafted or rendered"
            sub = "BLOCKS STAGE 02 AND STAGE 04"
        elif not narr["usable"]:
            text = ("The narrative key failed its last test — the key is "
                    "there, the engine will not run") if narr["failed"]                 else "No narrative model — nothing can be read or drafted"
            sub = "BLOCKS STAGE 02 — RENDERING STILL RUNS"
        else:
            text = ("Every image engine failed its last test — the keys are "
                    "there, the engines will not run") if img["failed"]                 else "No image engine — nothing can be rendered"
            sub = "BLOCKS STAGE 04 — RESEARCH STILL RUNS"
        out.append({
            "kind": "KEY", "action": "settings", "scope": "install",
            "stages": stages, "stage": stages[0] if stages else "wizard",
            "text": text, "sub": sub,
            "detail": "Settings → AI & engines. One OpenRouter connection "
                      "serves both roles.",
        })

    if not app_state.get("screenplay"):
        out.append({"kind": "GAP", "text": "Screenplay not uploaded",
                    "action": "dashboard"})
    if not any(r["role"] == "BOARD_LAYOUT_STYLE" and r["status"] == "APPROVED"
               for r in refs):
        out.append({"kind": "GAP",
                    "text": "Board layout master (BOARD_LAYOUT_STYLE) not "
                            "approved — needed to ASSEMBLE boards, not to "
                            "render panels",
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
    # One row per UNIT (2026-08-13): revisions share one board, so the
    # slot map is evaluated once per base with a locked revision.
    from . import assemble, revisions
    seen_bases: set[str] = set()
    for meta in specs:
        if not meta["locked"]:
            continue
        sid = revisions.base_of(meta["specification_id"])
        if sid in seen_bases:
            continue
        seen_bases.add(sid)
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

    # A consolidation that did not happen (adversarial review F23). It is
    # advisory rather than blocking — nothing is broken — but it is the one
    # state in which the retired revision machinery still matters, so it
    # must be visible instead of only logged.
    try:
        from . import revisions as _rev
        for sk in _rev.skipped_migrations():
            out.append({
                "kind": "CARE", "action": "specs", "spec_id": sk.get("base", ""),
                "text": f"{sk.get('base', '')} did not consolidate at boot — "
                        f"{sk.get('reason', 'reason not recorded')}. Its revision "
                        "chain is still split, so its board picks takes by the "
                        "old rules.",
            })
    except Exception:  # noqa: BLE001 — an advisory row must never break the list
        pass

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
    key = rec.get("sha256") or rec["file"]
    if key in _text_cache:
        return _text_cache[key]
    # One extraction, done at import (store.set_screenplay) and reused by
    # every feature AND every model call; legacy uploads backfill there.
    text = store.screenplay_text_cached()
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


def scene_anchor(subject: str, max_chars: int = 7000) -> dict:
    """Deterministic subject→slugline anchor for breakdowns (user-hit
    2026-08-06: a run for INT_BRIEFING_ROOM_DAY_V01 drafted the crash
    site — a machine slug left to model fuzzy-matching, and it lost).
    The subject is de-slugged (underscores, INT/EXT, times, Vnn stripped)
    and matched against the screenplay's own slugline parse; on a match
    the actual scene text is returned for verbatim quoting into the
    instructions, so the model never has to find the scene itself."""
    text = screenplay_text()
    if not text.strip():
        return {"matched": False}
    lines = text.splitlines()
    scenes: list[dict] = []
    for i, raw in enumerate(lines):
        stripped = raw.strip()
        if not stripped or len(stripped) > 90 or stripped != stripped.upper():
            continue
        m = _SLUG_RE.match(stripped)
        if not m:
            continue
        place = re.split(r"\s+[-–—]\s+", m.group(2))[0].strip(" .-–—")
        place = _strip_time_tail(place)
        if place:
            scenes.append({"line": i, "heading": stripped, "location": place})
    if not scenes:
        return {"matched": False}

    def norm(v: str) -> str:
        return " ".join(re.sub(r"[^a-z0-9]+", " ", v.lower()).split())

    subj = re.sub(r"\bv\d+\b", " ", norm(subject))
    subj = re.sub(r"\b(int|ext|i e|day|night|dawn|dusk|morning|evening|"
                  r"continuous|later)\b", " ", subj)
    subj = " ".join(subj.split())
    if len(subj) < 3:
        return {"matched": False}
    subj_words = set(subj.split())

    # The MOST SPECIFIC match, not the first one found (user-hit
    # 2026-08-16). A board set in "TERRA NOVA SECURE BAY" anchored to
    # "TERRA NOVA" — a real but different slugline that happens to be a
    # prefix — and every downstream reader got the wrong scene: the
    # composition check judged framing against an exterior space battle,
    # and a screenplay scan reported, honestly and uselessly, that the
    # text did not mention the airlock. Both matched, so nothing looked
    # broken. Longest location wins; ties go to the earliest scene.
    # Direction matters, not just length. A location CONTAINED IN the
    # subject is the subject naming a place, and the longest such is the
    # most specific reading of it ("terra nova secure bay" over "terra
    # nova"). A location that CONTAINS the subject is the subject being
    # vaguer than the screenplay, and there the shortest is the least
    # invented — asking for "terra nova" must not land on "terra nova
    # hangar 02", which was the first fix's own overshoot.
    inside = [sc for sc in scenes
              if norm(sc["location"])
              and f" {norm(sc['location'])} " in f" {subj} "]
    if inside:
        best = max(inside, key=lambda sc: (len(norm(sc["location"]).split()),
                                           -sc["line"]))["location"]
        hits = [sc for sc in scenes if sc["location"] == best]
    else:
        hits = [sc for sc in scenes
                if norm(sc["location"])
                and f" {subj} " in f" {norm(sc['location'])} "]
        if hits:
            best = min(hits, key=lambda sc: (len(norm(sc["location"]).split()),
                                             sc["line"]))["location"]
            hits = [sc for sc in scenes if sc["location"] == best]
    if not hits:
        # every substantial location token present in the subject
        loose = [sc for sc in scenes
                 if (lambda toks: toks and all(t in subj_words for t in toks))(
                     [t for t in norm(sc["location"]).split() if len(t) >= 3])]
        if not loose:
            return {"matched": False}
        best = max(loose, key=lambda sc: (len(norm(sc["location"]).split()),
                                          -sc["line"]))["location"]

    chunks = []
    picked = 0
    for idx, sc in enumerate(scenes):
        if sc["location"] != best:
            continue
        picked += 1
        end = scenes[idx + 1]["line"] if idx + 1 < len(scenes) else len(lines)
        chunks.append("\n".join(lines[sc["line"]:end]).strip())
    quoted = "\n\n".join(chunks)
    if len(quoted) > max_chars:
        quoted = quoted[:max_chars] + "\n[… scene text truncated …]"
    return {"matched": True, "location": best, "scenes": picked,
            "text": quoted}


# --------------------------------------------------------------------- acts

_ACT_RE = re.compile(
    r"^\s*ACT\s+(ONE|TWO|THREE|FOUR|FIVE|IV|V|I{1,3}|[1-5])\b"
    r"[\s.:\-‐‑‒–—―]*(.*?)\s*$", re.I)
_ACT_WORD = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5,
             "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
             "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}


def _acts(lines: list[str], scenes: list[dict]) -> dict:
    """Three acts over the screenplay, chronologically.

    A screenplay that MARKS its acts gets its own divisions and its own
    titles — that is the author's structure and we do not second-guess it.
    Most features do not mark them, so the fallback is the standard
    three-act split by scene position (25/50/25), unnamed: `ACT I` with no
    title is honest, while a title we invented would be a claim about the
    script we cannot support.

    Returns {acts: [...], derived: bool}; each act carries the scene index
    range it owns, so a location is placed by the act its FIRST scene sits
    in — where it enters the story.
    """
    marks = []
    for i, raw in enumerate(lines):
        t = raw.strip()
        if not t or len(t) > 60:
            continue
        m = _ACT_RE.match(t)
        if not m:
            continue
        n = _ACT_WORD.get(m.group(1).upper())
        if not n or any(x["n"] == n for x in marks):
            continue
        title = re.sub(r"[\s.:\-–—]+$", "", m.group(2) or "").strip()
        # a marker in dialogue or action is not a division; act headings
        # sit alone in caps
        if t != t.upper():
            continue
        marks.append({"n": n, "line": i, "title": title})
    marks.sort(key=lambda x: x["line"])

    total = len(scenes)
    if len(marks) >= 2 and total:
        acts = []
        for k, mk in enumerate(marks):
            end_line = marks[k + 1]["line"] if k + 1 < len(marks) else len(lines)
            first = next((idx for idx, sc in enumerate(scenes)
                          if sc["line"] >= mk["line"]), total)
            last = next((idx for idx, sc in enumerate(scenes)
                         if sc["line"] >= end_line), total)
            acts.append({"n": mk["n"], "roman": _ROMAN.get(mk["n"], str(mk["n"])),
                         "title": mk["title"], "start": first, "end": last})
        if any(a["end"] > a["start"] for a in acts):
            return {"acts": acts, "derived": True}

    # The standard shape, unnamed.
    cut1, cut2 = round(total * 0.25), round(total * 0.75)
    return {"derived": False, "acts": [
        {"n": 1, "roman": "I", "title": "", "start": 0, "end": cut1},
        {"n": 2, "roman": "II", "title": "", "start": cut1, "end": cut2},
        {"n": 3, "roman": "III", "title": "", "start": cut2, "end": total},
    ]}


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
        # chronological identity: a location belongs to the act it ENTERS
        # the story in, which is the act of its first scene.
        g.setdefault("first_line", sc["line"])
        g.setdefault("first_index", None)

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

    act_info = _acts(lines, scenes)
    index_of = {sc["line"]: i for i, sc in enumerate(scenes)}

    def act_of(first_line: int) -> int:
        i = index_of.get(first_line, 0)
        for a in act_info["acts"]:
            if a["start"] <= i < a["end"]:
                return a["n"]
        return act_info["acts"][-1]["n"]

    out = []
    # Chronological (user 2026-08-16). Scene COUNT was the old order and it
    # answered "which location is biggest" — a different question from the
    # one a location list is asked, which is where the story goes.
    for g in sorted(groups.values(), key=lambda x: x["first_line"]):
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
            "first_line": g["first_line"],
            "act": act_of(g["first_line"]),
            "sheet": ({"spec_id": match["spec_id"], "locked": match["locked"],
                       "status": match["status"]} if match else None),
        })
    return {"available": True, "locations": out,
            "acts": act_info["acts"], "acts_derived": act_info["derived"],
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


# ------------------------------------------------- the one citation predicate

def screenplay_haystack() -> tuple[str, str]:
    """The screenplay in both comparison forms, once. Callers that check
    many quotes in a loop should hold this rather than re-normalise a
    130 KB document per row."""
    text = _norm(screenplay_text())
    return text, _squash(text)


def quote_is_in_screenplay(quote: str, hay: tuple[str, str] | None = None) -> bool:
    """Does the screenplay actually contain this citation?

    ONE predicate, four callers (F21/F6/F7, adversarial review 2026-08-17):
    `autofill._coerce` when the narrative model classifies a row,
    `scan._coerce` when a scan proposes one, `store.amend_panel_objects`
    when one is written by hand, and `citation_check` when they are
    re-verified later. Before this existed the app verified the class it
    could NOT check — a WEAK_INFERENCE cannot self-promote — and skipped
    the only falsifiable one: SCRIPT_EXPLICIT asserts that a verbatim line
    exists in a document the server is holding, and nothing opened it.

    Tolerant in the same two steps citation_check has always used, because
    PDF extraction mangles spacing and dashes: normalised containment
    first, bare letters-and-digits second. A citation only counts as absent
    when even its letters are gone.

    An empty screenplay returns False for everything — no screenplay means
    nothing can be sourced to it, which is the honest answer rather than a
    free pass.
    """
    q = str(quote or "").strip()
    if len(q) < 12:          # too short to be a citation, same floor as _QUOTE_RE
        return False
    text, squashed = hay if hay is not None else screenplay_haystack()
    if not text:
        return False
    return _norm(q) in text or _squash(q) in squashed


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
            # A row's citation is its `quote` field. `_QUOTE_RE` over
            # `source` stays as the LEGACY reader for rows written before
            # that field existed — and it is why this check used to be
            # blind to the newest rows: it only ever inspected text inside
            # literal quote marks, and a row whose source was the bare
            # sentence never incremented `checked` at all (F7).
            quotes = [str(row.get("quote", "")).strip()] if row.get("quote") \
                else _QUOTE_RE.findall(str(row.get("source", "")))
            for quote in quotes:
                if not quote:
                    continue
                checked += 1
                if not quote_is_in_screenplay(quote, (text, squashed)):
                    missing.append({
                        "spec_id": sid,
                        "object_id": row.get("object_id", ""),
                        "panel_id": row.get("panel_id", ""),
                        "object": row.get("object", ""),
                        "quote": quote,
                        "locked": meta["locked"],
                    })
            # A row claiming the screenplay with nothing to show is itself
            # a finding, not an absence of one (review F7).
            if str(row.get("evidence_class", "")) == "SCRIPT_EXPLICIT" and not quotes:
                checked += 1
                missing.append({
                    "spec_id": sid,
                    "object_id": row.get("object_id", ""),
                    "panel_id": row.get("panel_id", ""),
                    "object": row.get("object", ""),
                    "quote": "",
                    "no_citation": True,
                    "locked": meta["locked"],
                })
    report = {"checked_at": store.utcnow(), "screenplay": rec.get("file", ""),
              "available": True, "quotes_checked": checked, "missing": missing}
    _save_citation_report(report)
    return report


def _save_citation_report(report: dict) -> None:
    store._atomic_write_json(_citation_report_path(), report)


def load_citation_report() -> dict | None:
    if not _citation_report_path().exists():
        return None
    try:
        return json.loads(_citation_report_path().read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
