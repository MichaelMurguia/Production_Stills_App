"""Process World Visualization: fill Production Design from the read.

User, 2026-10-04: "Once the screenplay is read, I want the Production
Design to fill out automatically ... make the art direction bible first,
then render the thumbnails." Rulings from the same conversation:

- The upload button is the consent. It reads "Process World
  Visualization", says it can take up to an hour, and its click pays for
  everything below. Nothing here runs a second time for the same draft.
- Style anchors the director has not set take the script's proposal. The
  card shows the chosen style with Change, and nothing else.
- Proposed design languages and environments are CONFIRMED, so the Bible
  covers every one. (This replaces "confirming is the director's act",
  Gap 5 ruling §1, for the first build of a draft.)
- Characters get a small portrait each, as a proposal awaiting the
  director's verdict. Vehicles and props stay on demand.
- Every image is a small thumbnail first.

The steps, in order, each reported as it runs:

  confirm  · anchors · bible · colour · languages · environments · cast

A step that fails is recorded and the build carries on where it still can:
thumbnails without a Bible are rendered as best guesses, and portraits
need a Bible, so they wait for one. A build runs once per screenplay
draft (`built_for` holds the draft's hash).

The production is fixed at the start. If the studio switches production
mid-build, the build stops before its next write and runs again on return,
because `paths` points every write at whichever production is active.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import threading
import traceback

from . import (bible, generate, language_previews, paths, store, wizard)

WORKERS = 3   # images rendered at once

STEPS = [
    ("confirm", "Confirming what the read found"),
    ("anchors", "Choosing the look from the script"),
    ("bible", "Writing the Art Direction Bible"),
    ("colour", "Proposing palettes"),
    ("languages", "Rendering design languages"),
    ("environments", "Rendering environments"),
    ("cast", "Rendering character portraits"),
]

_lock = threading.Lock()
_running: dict[str, threading.Thread] = {}


class Stopped(Exception):
    pass


def _path():
    return paths.DATA / "world_build.json"


def _sha() -> str:
    return str((store.load_app_state().get("screenplay") or {}).get("sha256", ""))


def _read() -> dict:
    try:
        rec = json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    # A finished build with failed steps is INCOMPLETE and not built,
    # including a record written before that rule existed (2026-10-04:
    # the first real build's renders all failed and it was stamped done).
    if rec.get("state") == "done" and any(
            s.get("state") == "failed" for s in rec.get("steps") or []):
        rec["state"] = "incomplete"
        rec.pop("built_for", None)
    return rec


def status() -> dict:
    rec = _read()
    slug = paths.ACTIVE_PROJECT
    with _lock:
        alive = slug in _running and _running[slug].is_alive()
    if rec.get("state") == "running" and not alive:
        # A record says running but no thread is: the server restarted
        # mid-build. Say so; the next start resumes from what is missing.
        rec["state"] = "interrupted"
    rec.setdefault("state", "idle")
    rec["needed"] = needed()
    # Whether THIS draft's build was ever started by a click. Only then may
    # an interrupted build resume on arrival; a draft read before the
    # button existed is offered the build instead (arriving is not consent).
    rec["consented"] = bool(rec.get("sha")) and rec.get("sha") == _sha()
    return rec


def needed() -> bool:
    """A build is due when there is a read of the current draft that has
    not been built yet."""
    a = store.load_wizard_analysis() or {}
    if not (a.get("design_worlds") or a.get("environments") or a.get("subjects")):
        return False
    sha = _sha()
    return bool(sha) and _read().get("built_for") != sha


def start() -> dict:
    """Start the build for the active production if it is due and not
    already running. Idempotent: asking twice never builds twice."""
    slug = paths.ACTIVE_PROJECT
    with _lock:   # status() takes this lock too, so it is read after
        t = _running.get(slug)
        if not (t and t.is_alive()) and needed():
            t = threading.Thread(target=_run, args=(slug, _sha()), daemon=True,
                                 name=f"world-build-{slug or 'default'}")
            _running[slug] = t
            _save(_fresh(_sha()))
            t.start()
    return status()


# ------------------------------------------------------------------ running

def _fresh(sha: str) -> dict:
    return {"state": "running", "sha": sha, "started_at": store.utcnow(),
            "step": "", "message": "Starting", "errors": [],
            "steps": [{"key": k, "label": l, "state": "waiting", "detail": ""}
                      for k, l in STEPS]}


def _save(rec: dict) -> None:
    paths.ensure_dirs()
    store._atomic_write_json(_path(), rec)


class _Run:
    def __init__(self, slug: str, sha: str):
        self.slug, self.sha = slug, sha
        # The exact data folder, not only the production's name: a home
        # that moved (another install, a test's temporary home) is as much
        # "not ours" as a switched production.
        self.data = paths.DATA
        rec = _read()
        # The record start() wrote, or a fresh one when run directly.
        self.rec = rec if rec.get("steps") and rec.get("sha") == sha else _fresh(sha)
        self.mutex = threading.RLock()   # error() re-enters step()

    def guard(self):
        if paths.ACTIVE_PROJECT != self.slug or paths.DATA != self.data:
            raise Stopped("the production was switched")

    def step(self, key: str, state: str, detail: str = ""):
        with self.mutex:
            for s in self.rec["steps"]:
                if s["key"] == key:
                    s["state"], s["detail"] = state, detail
                    if state == "now":
                        self.rec["step"] = key
                        self.rec["message"] = s["label"] + (f" · {detail}" if detail else "")
            self.guard()
            _save(self.rec)

    def error(self, key: str, err: Exception):
        with self.mutex:
            self.rec["errors"].append({"step": key, "error": str(err)[:300]})
        self.step(key, "failed", str(err)[:160])


def _run(slug: str, sha: str) -> None:
    run = _Run(slug, sha)
    try:
        for key, _label in STEPS:
            run.guard()
            fn = globals()[f"_step_{key}"]
            run.step(key, "now")
            try:
                detail = fn(run) or ""
                run.step(key, "done", detail)
            except Stopped:
                raise
            except Exception as e:      # recorded; the build carries on
                traceback.print_exc()
                run.error(key, e)
        run.guard()
        with run.mutex:
            failed = [s for s in run.rec["steps"] if s["state"] == "failed"]
            if failed:
                # Not marked built: the draft stays due, and running it
                # again redoes only what is missing (every step skips work
                # already done). User-hit 2026-10-04: every render failed
                # and the build still read as done, so nothing would ever
                # retry it.
                run.rec.update(state="incomplete", finished_at=store.utcnow(),
                               step="", message=f"{len(failed)} step"
                               f"{'s' if len(failed) != 1 else ''} did not finish")
            else:
                run.rec.update(state="done", built_for=sha, finished_at=store.utcnow(),
                               step="", message="World visualized")
            _save(run.rec)
    except Stopped as e:
        # Not written: the switched-to production's folder is not ours.
        print(f"[world build] {slug}: stopped — {e}")
    finally:
        with _lock:
            if _running.get(slug) is threading.current_thread():
                del _running[slug]


# ------------------------------------------------------------------- steps

def _step_confirm(run: _Run) -> str:
    a = store.load_wizard_analysis() or {}
    n = 0
    for field in ("design_worlds", "environments"):
        for item in a.get(field) or []:
            if item.get("status") == "PROPOSED":
                item.pop("status", None)
                n += 1
    run.guard()
    store.save_wizard_analysis(a)
    return f"{n} confirmed" if n else "nothing to confirm"


ANCHOR_FIELDS = {"texture": "texture", "cinematography": "light", "rendering": "medium"}


def _step_anchors(run: _Run) -> str:
    answers = store.interview_answers()
    empty = [p for p, f in ANCHOR_FIELDS.items() if not answers.get(f, "").strip()]
    if not empty:
        return "already set"
    got = wizard.suggest_anchors(generate.narrative_default())
    props = got.get("proposals") or {}
    set_ = []
    for p in empty:
        val = str((props.get(p) or {}).get("value", "")).strip()
        if val:
            answers[ANCHOR_FIELDS[p]] = val
            set_.append((props.get(p) or {}).get("name") or p)
    run.guard()
    store._atomic_write_json(paths.DATA / "interview.json", answers)
    bible.sync_from_anchors()
    return ", ".join(set_) if set_ else "no proposal"


def _bible_answers() -> dict:
    """What the Create button sends the drafter, assembled server-side."""
    a = store.load_wizard_analysis() or {}
    iv = store.interview_answers()
    qa = [f"Q: {q} / A: {a['question_answers'][q]['answer']}"
          for q in (a.get("unresolved") or [])
          if (a.get("question_answers") or {}).get(q, {}).get("answer")]
    return {
        "worlds": [{"name": str(w.get("name", "")).strip(),
                    "notes": str(w.get("description", "")).strip(),
                    "keywords": w.get("keywords") or []}
                   for w in a.get("design_worlds") or [] if str(w.get("name", "")).strip()],
        "environments": [{"name": str(e.get("name", "")).strip(),
                          "notes": str(e.get("notes", "")).strip()}
                         for e in a.get("environments") or [] if str(e.get("name", "")).strip()],
        "texture": iv.get("texture", ""), "palette": iv.get("palette", ""),
        "light": iv.get("light", ""), "medium": iv.get("medium", ""),
        "never": iv.get("never", ""),
        "notes": "\n".join(x for x in [iv.get("notes", ""), *qa] if x),
        "ref_ids": [r["id"] for r in store.auto_style_references()],
    }


def _step_bible(run: _Run) -> str:
    if bible.load_text().strip():
        return "already written"
    r = wizard.draft_bible(_bible_answers(), generate.narrative_default())
    text = str(r.get("markdown", "")).strip()
    if not text:
        raise RuntimeError("the drafter returned an empty Bible")
    run.guard()
    bible.save_document(text)
    return f"written by {r.get('model') or 'the model'}"


def _step_colour(run: _Run) -> str:
    if not bible.load_text().strip():
        return "waits for the Bible"
    have = [r for r in store.list_references()
            if store.role_head(r.get("role", "")) == "COLOR_PALETTE"]
    if have:
        return "already proposed"
    sw = wizard.generate_swatches(generate.narrative_default(), None, "", False)
    n = sum(len(g.get("swatches") or []) for g in (sw or {}).get("groups") or [])
    return f"{n} swatches proposed, awaiting approval"


def _render_many(run: _Run, key: str, names: list, fn) -> str:
    if not names:
        return "nothing to render"
    if not generate.image_engine():
        raise RuntimeError("no image model connected")
    done, failed = 0, []
    run.step(key, "now", f"0 of {len(names)}")
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(fn, n): n for n in names}
        for f in cf.as_completed(futs):
            try:
                f.result()
                done += 1
            except Exception as e:
                failed.append(f"{futs[f]}: {e}")
            run.step(key, "now", f"{done} of {len(names)}")
    if failed and not done:
        raise RuntimeError(failed[0])
    with run.mutex:
        run.rec["errors"] += [{"step": key, "error": x[:300]} for x in failed]
    return f"{done} rendered" + (f", {len(failed)} failed" if failed else "")


def _step_languages(run: _Run) -> str:
    return _render_many(run, "languages", language_previews.due("language"),
                        lambda n: language_previews.render(n, "language"))


def _step_environments(run: _Run) -> str:
    return _render_many(run, "environments", language_previews.due("environment"),
                        lambda n: language_previews.render(n, "environment"))


def _step_cast(run: _Run) -> str:
    """Characters only (user ruling). Each is cast from the read if it is
    not yet, then given one small portrait that waits for a verdict."""
    if not bible.load_text().strip():
        return "waits for the Bible"
    a = store.load_wizard_analysis() or {}
    have = {s["name"].casefold(): s for s in store.list_subjects()}
    todo = []
    for subj in a.get("subjects") or []:
        if str(subj.get("kind", "")).upper() != "CHARACTER":
            continue
        name = str(subj.get("name", "")).strip()
        if not name:
            continue
        rec = have.get(name.casefold())
        if rec is None:
            run.guard()
            rec = store.add_subject(name, "CHARACTER", str(subj.get("subtitle", "")),
                                    subj.get("traits") or [], "read")
            if str(subj.get("description", "")).strip():
                rec = store.update_subject(rec["id"],
                                           {"description": str(subj["description"])})
        if not rec.get("ref_ids") and (rec.get("description") or rec.get("traits")):
            todo.append(rec["id"])
    eng = generate.image_engine()
    return _render_many(run, "cast", todo, lambda sid: generate.subject_portrait(
        sid, eng, size=generate.thumb_size(eng), quality="medium"))
