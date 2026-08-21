"""The tutorial system: authored onboarding, as content rather than code.

Three facts shape this module.

**Content is files, not code.** A tutorial is one JSON document. Packaged
tutorials live in `app/content/tutorials/` and travel with the app — the
fleet auto-updates on every push, so publishing a first-run experience or
a release announcement is a commit, reviewable as a diff and versioned
with the code that it explains. A studio that authors its own gets
`SCREENBOARD_HOME/tutorials/`, which survives deploys because HOME is the
persistent volume. Resolution merges the two, install wins by id, and a
`{"deleted": true}` stub hides a packaged tutorial without editing the
package.

**Content never names a CSS selector.** Steps name an *anchor* —
`stage.screenplay`, `settings.engines` — and `content/tutorial_schema.json`
maps anchors to selectors. When the markup moves, one line there changes
and every authored tutorial still lands on the right control. That file is
also the single declaration of the predicate vocabulary: this module
validates against it, the editor builds its dropdowns from it, and
`tutorial.js` evaluates exactly the kinds it lists (asserted by test).

**Authoring is owner-only; consuming is everyone.** The editor and every
mutating route sit behind the same gate as Debug tools
(`SCREENBOARD_DEBUG_TOOLS`) — customers see tutorials, never the CMS. The
read route is open, because a customer's studio must be able to run the
FTUE.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import paths

PACKAGED = Path(__file__).resolve().parent / "content" / "tutorials"
SCHEMA_FILE = Path(__file__).resolve().parent / "content" / "tutorial_schema.json"

ID_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}")
# Same-origin app paths only. A tutorial that could send a studio to
# another host would be a phishing surface authored through a text box.
PATH_RE = re.compile(r"/(?!/)[A-Za-z0-9/_.\-%]*$")

STATUSES = ("seen", "completed", "dismissed")


# ------------------------------------------------------------------ places

def install_dir() -> Path:
    """Per-studio authored content. Under HOME, so a cloud studio's own
    tutorials survive every deploy."""
    return paths.HOME / "tutorials"


def can_ship() -> bool:
    """True where saving a tutorial writes the SHIPPED copy — a git
    checkout, which is the owner's machine. Deploys carry no .git (the
    same fact `_app_sha` reads), so a cloud studio edits its own copy and
    the UI says so instead of implying a fleet-wide publish that could
    never happen."""
    return (paths.ROOT / ".git").exists()


def target_dir() -> Path:
    """Where a save lands. On a checkout that is the packaged directory —
    authoring IS editing the product, and `git push` is the publish step.
    Anywhere else it is the studio's own directory."""
    return PACKAGED if can_ship() else install_dir()


def state_file() -> Path:
    return paths.HOME / "tutorial_state.json"


def version() -> str:
    f = paths.ROOT / "VERSION"
    try:
        return f.read_text(encoding="utf-8").strip() or "dev"
    except OSError:
        return "dev"


# ------------------------------------------------------------------ schema

def schema() -> dict:
    return json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))


def anchors() -> list[dict]:
    return schema()["anchors"]


def anchor_names() -> set[str]:
    return {a["name"] for a in anchors()}


# ------------------------------------------------------------------- files

def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _read_dir(d: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not d.exists():
        return out
    for f in sorted(d.glob("*.json")):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # A corrupt file must never take the studio's onboarding down
            # with it; it is reported by the CMS list, not raised here.
            continue
        if isinstance(doc, dict) and isinstance(doc.get("id"), str):
            out[doc["id"]] = doc
    return out


def resolved() -> list[dict]:
    """Every live tutorial, packaged overridden by install, highest
    priority first. Each carries `source` — the CMS states where a row
    comes from, because "edited here" and "shipped with the app" are
    different facts about the same id."""
    packaged = _read_dir(PACKAGED)
    local = _read_dir(install_dir())
    merged: dict[str, dict] = {}
    for tid, doc in packaged.items():
        merged[tid] = {**doc, "source": "packaged"}
    for tid, doc in local.items():
        if doc.get("deleted"):
            merged.pop(tid, None)
            continue
        merged[tid] = {**doc, "source": "install",
                       "overrides_packaged": tid in packaged}
    rows = list(merged.values())
    rows.sort(key=lambda d: (-int(d.get("priority") or 0), str(d.get("id"))))
    return rows


def live() -> list[dict]:
    """What the runtime is allowed to consider: enabled tutorials that
    validate. Broken content is inert, never half-run."""
    return [d for d in resolved()
            if d.get("enabled", True) and not validate(d)]


def get(tid: str) -> dict | None:
    for d in resolved():
        if d["id"] == tid:
            return d
    return None


def save(doc: dict) -> dict:
    """Validate then write. Raises ValueError with every problem at once —
    an editor that reports one error per save is a bad editor."""
    errors = validate(doc)
    if errors:
        raise ValueError("; ".join(errors))
    clean = {k: v for k, v in doc.items()
             if k not in ("source", "overrides_packaged", "state")}
    clean["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _atomic_write_json(target_dir() / f"{clean['id']}.json", clean)
    return get(clean["id"]) or clean


def delete(tid: str) -> None:
    """Remove a tutorial. On a checkout the packaged file goes; in a
    studio a tombstone hides it, because a studio cannot edit the
    package."""
    tid = _safe_id(tid)
    local = install_dir() / f"{tid}.json"
    packaged = PACKAGED / f"{tid}.json"
    if can_ship():
        packaged.unlink(missing_ok=True)
        local.unlink(missing_ok=True)
        return
    if packaged.exists():
        _atomic_write_json(local, {"id": tid, "deleted": True})
    else:
        local.unlink(missing_ok=True)


def _safe_id(tid: str) -> str:
    if not ID_RE.fullmatch(str(tid or "")):
        raise KeyError(tid)
    return tid


# -------------------------------------------------------------- validation

def _predicate_errors(p, ctx: str, where: str, spec: dict,
                      anchor_set: set[str], views: set[str]) -> list[str]:
    """One predicate, checked against the declared vocabulary.

    `ctx` is where it appears — trigger / skip_if / advance. A predicate
    is refused in a context it cannot work in: `{"first_run": true}` as an
    *advance* condition would never fire, and a tutorial that hangs on
    step 2 forever is worse than one that fails to save.
    """
    if p in (None, {}):
        return []
    if not isinstance(p, dict):
        return [f"{where}: a condition must be an object"]
    if len(p) != 1:
        return [f"{where}: a condition holds exactly one of "
                f"{', '.join(sorted(spec))}"]
    kind, arg = next(iter(p.items()))
    if kind not in spec:
        return [f"{where}: unknown condition '{kind}'"]
    decl = spec[kind]
    if ctx not in decl["use"]:
        return [f"{where}: '{kind}' cannot be used as {ctx} "
                f"(allowed: {', '.join(decl['use'])})"]
    errs: list[str] = []
    a = decl["arg"]
    if a == "none":
        if arg is not True:
            errs.append(f"{where}: '{kind}' takes true")
    elif a in ("string", "path"):
        if not isinstance(arg, str) or not arg.strip():
            errs.append(f"{where}: '{kind}' needs a non-empty string")
    elif a == "view":
        if arg not in views:
            errs.append(f"{where}: '{kind}' — unknown view '{arg}'")
    elif a == "anchor":
        if arg not in anchor_set:
            errs.append(f"{where}: '{kind}' — unknown anchor '{arg}'")
    elif a == "tutorial":
        if not isinstance(arg, str) or not ID_RE.fullmatch(arg or ""):
            errs.append(f"{where}: '{kind}' needs a tutorial id")
    elif a == "path_value":
        if not isinstance(arg, dict) or not isinstance(arg.get("path"), str):
            errs.append(f"{where}: '{kind}' needs {{path, value}}")
    elif a == "api":
        if not isinstance(arg, dict) or not isinstance(arg.get("path"), str):
            errs.append(f"{where}: '{kind}' needs {{method, path}}")
        else:
            if arg.get("method") and str(arg["method"]).upper() not in (
                    "GET", "POST", "PUT", "PATCH", "DELETE"):
                errs.append(f"{where}: '{kind}' — unknown method")
            try:
                re.compile(arg["path"])
            except re.error:
                errs.append(f"{where}: '{kind}' — path is not a valid pattern")
    elif a == "list":
        if not isinstance(arg, list) or not arg:
            errs.append(f"{where}: '{kind}' needs a non-empty list")
        else:
            for i, sub in enumerate(arg):
                errs += _predicate_errors(sub, ctx, f"{where} → {kind}[{i}]",
                                          spec, anchor_set, views)
    elif a == "predicate":
        errs += _predicate_errors(arg, ctx, f"{where} → not", spec,
                                  anchor_set, views)
    return errs


TUTORIAL_KEYS = {"id", "rev", "kind", "title", "note", "enabled", "priority",
                 "trigger", "replayable", "steps", "updated", "deleted"}
STEP_KEYS = {"id", "surface", "anchor", "side", "align", "title", "body",
             "goto", "skip_if", "advance", "wait", "block", "act", "optional"}


def validate(doc: dict) -> list[str]:
    """Every problem with a document, as sentences. Empty list = usable."""
    s = schema()
    spec = s["predicates"]
    anchor_set = anchor_names()
    views = set(s["views"])
    e: list[str] = []
    if not isinstance(doc, dict):
        return ["a tutorial must be an object"]
    if doc.get("deleted"):
        return [] if ID_RE.fullmatch(str(doc.get("id") or "")) else ["bad id"]

    unknown = set(doc) - TUTORIAL_KEYS - {"source", "overrides_packaged"}
    if unknown:
        e.append(f"unknown field(s): {', '.join(sorted(unknown))}")
    if not ID_RE.fullmatch(str(doc.get("id") or "")):
        e.append("id must be lowercase letters, digits, dot, dash or "
                 "underscore, starting with a letter or digit")
    if not str(doc.get("title") or "").strip():
        e.append("title is required — it is what the CMS list shows")
    if doc.get("kind") not in s["kinds"]:
        e.append(f"kind must be one of {', '.join(sorted(s['kinds']))}")
    rev = doc.get("rev", 1)
    if not isinstance(rev, int) or rev < 1:
        e.append("rev must be a whole number from 1 up — raising it shows "
                 "the tutorial again to everyone who saw the last one")
    if not isinstance(doc.get("priority", 0), int):
        e.append("priority must be a whole number")
    e += _predicate_errors(doc.get("trigger"), "trigger", "trigger", spec,
                           anchor_set, views)

    steps = doc.get("steps")
    if not isinstance(steps, list) or not steps:
        e.append("a tutorial needs at least one step")
        return e
    seen_ids = set()
    for i, st in enumerate(steps):
        w = f"step {i + 1}"
        if not isinstance(st, dict):
            e.append(f"{w}: must be an object")
            continue
        bad = set(st) - STEP_KEYS
        if bad:
            e.append(f"{w}: unknown field(s): {', '.join(sorted(bad))}")
        sid = str(st.get("id") or "")
        if sid:
            if sid in seen_ids:
                e.append(f"{w}: duplicate step id '{sid}'")
            seen_ids.add(sid)
        surface = st.get("surface", "modal")
        if surface not in s["surfaces"]:
            e.append(f"{w}: surface must be one of "
                     f"{', '.join(sorted(s['surfaces']))}")
        if surface == "spotlight":
            if st.get("anchor") not in anchor_set:
                e.append(f"{w}: a spotlight step needs a known anchor "
                         f"(got '{st.get('anchor', '')}')")
        elif surface == "page" and st.get("anchor"):
            e.append(f"{w}: a page step takes no anchor — it exists for the "
                     "case where pointing at one control would be wrong")
        elif surface == "page" and st.get("block"):
            e.append(f"{w}: a page step cannot block — leaving the page "
                     "usable is the whole point of it")
        elif st.get("anchor") and st["anchor"] not in anchor_set:
            e.append(f"{w}: unknown anchor '{st['anchor']}'")
        if st.get("side") and st["side"] not in s["sides"]:
            e.append(f"{w}: side must be one of {', '.join(s['sides'])}")
        if st.get("align") and st["align"] not in s["aligns"]:
            e.append(f"{w}: align must be one of {', '.join(s['aligns'])}")
        if not str(st.get("title") or "").strip() \
                and not str(st.get("body") or "").strip():
            e.append(f"{w}: needs a title or a body — a blank step is a "
                     "scrim with nothing to read")
        for field in ("goto",):
            v = st.get(field)
            if v is not None and not PATH_RE.fullmatch(str(v)):
                e.append(f"{w}: {field} must be a path inside this app, "
                         "starting with a single /")
        act = st.get("act")
        if act is not None:
            if not isinstance(act, dict) or not str(act.get("label") or "").strip():
                e.append(f"{w}: act needs a label")
            elif act.get("goto") is not None \
                    and not PATH_RE.fullmatch(str(act["goto"])):
                e.append(f"{w}: act.goto must be a path inside this app")
        e += _predicate_errors(st.get("skip_if"), "skip_if", f"{w} skip_if",
                               spec, anchor_set, views)
        e += _predicate_errors(st.get("advance"), "advance", f"{w} advance",
                               spec, anchor_set, views)
        if st.get("wait") is not None and not isinstance(st["wait"], str):
            e.append(f"{w}: wait is the line shown while the step waits — "
                     "it must be text")
    return e


# ------------------------------------------------------------------- state

def load_state() -> dict:
    try:
        data = json.loads(state_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"tutorials": {}}
    if not isinstance(data, dict):
        return {"tutorials": {}}
    data.setdefault("tutorials", {})
    return data


def record(tid: str, status: str, step: int = 0, rev: int = 1) -> dict:
    """What this install has seen. Install-level, not per-production: a
    tutorial teaches the app, and meeting it once per production would be
    the app nagging."""
    tid = _safe_id(tid)
    if status not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")
    st = load_state()
    row = st["tutorials"].get(tid, {})
    row.update({
        "status": status,
        "step": max(int(step or 0), 0),
        "rev": int(rev or 1),
        "version": version(),
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    row.setdefault("first_seen", row["updated"])
    st["tutorials"][tid] = row
    _atomic_write_json(state_file(), st)
    return st


def reset(tid: str | None = None) -> dict:
    """Forget one tutorial or all of them — the act that makes authoring
    possible at all, since an FTUE is otherwise a thing you can only see
    once per install."""
    st = load_state()
    if tid is None:
        st["tutorials"] = {}
    else:
        st["tutorials"].pop(_safe_id(tid), None)
    _atomic_write_json(state_file(), st)
    return st


def export_bundle() -> dict:
    """Everything the runtime needs in one call: content, the anchor map,
    what this install has seen, and the running version (announcements
    compare against it).

    The anchors ride the PUBLIC bundle deliberately — a customer's studio
    has to resolve them to run its FTUE, and they are selectors for the
    app's own chrome, not anything privileged."""
    return {"tutorials": live(), "state": load_state()["tutorials"],
            "version": version(), "anchors": anchors()}
