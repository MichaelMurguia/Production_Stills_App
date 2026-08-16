from __future__ import annotations

import hmac
import json
import os

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               RedirectResponse, Response)
from fastapi.staticfiles import StaticFiles

from . import (activity, assemble, autofill, backup, bible, composition,
               connectors, generate, insights, looks, paths, sheet,
               sheet_render, store, wizard)
from .validation import check_spec, full_validate

app = FastAPI(title="Screenboard Studio", version="0.2.0")
paths.ensure_dirs()

# ---------------------------------------------------- cloud workspace gate
# Set SCREENBOARD_ACCESS_TOKEN and the whole app sits behind a login that
# accepts exactly that token (hosted tenants get theirs at purchase).
# Unset — every standalone install — none of this exists and the app stays
# fully offline-capable.
ACCESS_TOKEN = os.environ.get("SCREENBOARD_ACCESS_TOKEN", "")
# The OAuth callback is exempt like every OAuth callback must be: the
# browser arrives from the provider, possibly on a host that never held
# the session cookie. Safe unauthenticated: pkce_finish only completes
# with the single-use server-stored verifier that an AUTHENTICATED
# /api/connectors/openrouter/auth call created, and a foreign code can
# never satisfy our challenge.
_AUTH_EXEMPT = {"/login", "/api/login", "/api/healthz", "/styles.css",
                "/favicon.ico", "/connectors/openrouter/callback"}

_LOGIN_HTML = r"""<!doctype html>
<html><head><meta charset="utf-8"><title>Screenboard Studio — workspace login</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/styles.css"></head>
<body class="gate-page">
<div class="panel" id="gate">
  <span class="brand-title">SCREENBOARD</span>
  <h2>Screenboard access</h2>
  <p class="hint">Paste the access token from your order confirmation.</p>
  <form id="f" class="row" style="margin-top:12px">
    <input type="password" id="tok" placeholder="access token" style="flex:1" autofocus>
    <button class="primary">Enter</button>
  </form>
  <p class="mini hidden" id="err" style="color:var(--bad);margin-top:8px">That token doesn't match this Screenboard.</p>
</div>
<div class="panel hidden" id="signing">
  <h2>Signing you in&hellip;</h2>
</div>
<script>
// Arriving with a store handoff (/login#token): never flash the token
// form — show the quiet signing-in state instead.
if (location.hash.length > 1) {
  document.getElementById("gate").classList.add("hidden");
  document.getElementById("signing").classList.remove("hidden");
}
// The deep link that hit the gate rides ?next= — sign-in lands there.
// Same-origin paths only: a value not starting with a single "/" (or
// trying "//host") falls back to "/".
const rawNext = new URLSearchParams(location.search).get("next") || "/";
const next = /^\/(?!\/)/.test(rawNext) ? rawNext : "/";
const attempt = async token => {
  const r = await fetch("/api/login", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }) });
  if (r.ok) { location.replace(next); return; }
  document.getElementById("signing").classList.add("hidden");
  document.getElementById("gate").classList.remove("hidden");
  document.getElementById("tok").classList.add("bad");
  document.getElementById("err").classList.remove("hidden");
};
document.getElementById("f").onsubmit = e => {
  e.preventDefault();
  attempt(document.getElementById("tok").value.trim());
};
// Storefront handoff: /login#<token> signs in without a paste. The
// fragment never reaches any server or log; strip it immediately.
if (location.hash.length > 1) {
  const t = decodeURIComponent(location.hash.slice(1));
  history.replaceState(null, "", "/login" + location.search);
  attempt(t);
}
</script></body></html>"""


@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Baseline hardening on every response — the app is an app, never a
    document to embed or sniff."""
    resp = await call_next(request)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    resp.headers.setdefault("Referrer-Policy", "no-referrer")
    if not request.url.path.startswith("/api/"):
        # The UI must never run stale: without this, browsers heuristically
        # cache app.js/styles.css and a hosted studio can keep an old build
        # after the server updates (observed live 2026-08-01). no-cache
        # forces an ETag revalidation per load — a 304 when unchanged, the
        # new file the moment a release lands.
        resp.headers.setdefault("Cache-Control", "no-cache")
    return resp


@app.middleware("http")
async def workspace_auth(request: Request, call_next):
    if not ACCESS_TOKEN or request.url.path in _AUTH_EXEMPT:
        return await call_next(request)
    if hmac.compare_digest(request.cookies.get("sb_session", ""), ACCESS_TOKEN):
        return await call_next(request)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "workspace login required"}, status_code=401)
    # A shared deep link must survive the gate: carry the destination so
    # signing in lands ON the addressed page, not on "/".
    from urllib.parse import quote
    nxt = quote(request.url.path, safe="/")
    dest = f"/login?next={nxt}" if nxt != "/" else "/login"
    return RedirectResponse(dest, status_code=303)


@app.get("/login")
def login_page():
    if not ACCESS_TOKEN:
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(_LOGIN_HTML)


@app.post("/api/login")
def api_login(body: dict, request: Request):
    if not ACCESS_TOKEN:
        raise HTTPException(404)
    if not hmac.compare_digest(str(body.get("token", "")), ACCESS_TOKEN):
        import time
        time.sleep(0.5)  # keep online guessing expensive (sync route → threadpool)
        raise HTTPException(401, "wrong token")
    resp = JSONResponse({"ok": True})
    # Hosted tenants sit behind Railway's TLS terminator — the request
    # scheme can read http there unless uvicorn trusts the proxy headers,
    # and this cookie IS the workspace token. Railway presence forces
    # Secure; localhost standalone (no token gate anyway) is unaffected.
    on_railway = bool(os.environ.get("RAILWAY_GIT_COMMIT_SHA"))
    resp.set_cookie("sb_session", ACCESS_TOKEN, max_age=30 * 24 * 3600,
                    httponly=True, samesite="lax",
                    secure=request.url.scheme == "https" or on_railway)
    return resp


@app.get("/api/preview-render")
def api_preview_render():
    """One approved panel, for the store's workspace door (S1).

    Deliberately NOT auth-exempt: this is the customer's artwork, and an
    open endpoint would publish it to anyone who guessed the subdomain.
    The storefront calls it server-to-server with the workspace access
    token it already holds.

    Returns the panel's identity, not its bytes — the caller fetches the
    image through the existing candidate route with the same credential.
    """
    import random

    approved = []
    for meta in store.list_specs():
        sid = meta["specification_id"]
        for c in generate.list_candidates(sid):
            if c.get("status") == "APPROVED":
                approved.append((sid, c))
    if not approved:
        # A stated empty, not a 404: "looked, found none" is a different
        # fact from "this studio has no such endpoint".
        return {"found": False, "production": store.project_name()}
    sid, cand = random.choice(approved)
    return {
        "found": True,
        "production": store.project_name(),
        "board": sid,
        "candidate": cand.get("candidate_id", ""),
        "image": f"/api/specs/{sid}/candidates/{cand.get('candidate_id', '')}/image",
        "count": len(approved),
    }


def _app_sha() -> str:
    """Short git sha of the serving checkout, resolved once at process
    start. The fixture recorder stamps it into every bundle so the replay
    harness can tell the designer when its copy of the app has drifted
    from what the fixtures were recorded against (HARNESS tooling,
    2026-08-13). Deploys carry no .git — Railway's env sha is the same
    fact from the platform; "unknown" means no provenance at all."""
    try:
        import subprocess
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           cwd=str(paths.ROOT), capture_output=True,
                           text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    env = os.environ.get("RAILWAY_GIT_COMMIT_SHA", "")
    return env[:7] if env else "unknown"


APP_SHA = _app_sha()


@app.get("/api/healthz")
def api_healthz():
    """Liveness, serving revision, and product version — the provisioner's
    readiness probe and the future update-notice's source of truth."""
    ver = paths.ROOT / "VERSION"
    return {"ok": True,
            "rev": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "local")[:12],
            "app_sha": APP_SHA,
            "version": ver.read_text(encoding="utf-8").strip()
                       if ver.exists() else "dev"}


# ------------------------------------------------------------------ projects
# One install holds many projects, each a full home (data/, project_state/,
# context/). Settings (API keys) are install-level and follow the user.
# The '' slug is the legacy root layout every existing install already has.

@app.get("/api/projects")
def api_list_projects() -> dict:
    projects = paths.list_projects()
    for p in projects:
        p["last_backup_at"] = backup.last_backup_at(p["slug"])
        p["days_since_backup"] = backup.days_since_backup(p["slug"])
    # First run (PRODUCTIONS_PLAN M6): nothing named, nothing in the root
    # layout — the app opens on "Name the show you're working on."
    first_run = (not any(p["slug"] for p in projects)
                 and paths.ACTIVE_PROJECT == ""
                 and not store.load_app_state().get("screenplay")
                 and not store.list_specs()
                 and not store.list_references())
    return {"active": paths.ACTIVE_PROJECT, "projects": projects,
            "first_run": first_run}


@app.get("/api/storage")
def api_storage() -> dict:
    """What this studio's volume is holding, and how much room is left.
    A cloud studio is one service with one volume; nothing measured it, so
    a full one first showed up as a 502 from a paid render (2026-08-07)."""
    from . import storage
    return storage.usage()


@app.get("/api/projects/safety-zip")
def api_safety_zip(slug: str = "") -> Response:
    """The newest pre-import safety copy, as a download. It was insurance
    with no way to collect it — written to the volume and unreachable."""
    if slug:
        paths.safe_id(slug)
    try:
        base = backup._project_base(slug)
    except KeyError as e:
        raise _err(e)
    zips = sorted(base.glob("pre-import-*.zip"), key=lambda z: z.stat().st_mtime)
    if not zips:
        raise HTTPException(404, "no safety copy — one is written before each import")
    newest = zips[-1]
    return Response(newest.read_bytes(), media_type="application/zip",
                    headers={"Content-Disposition":
                             f'attachment; filename="{newest.name}"'})


@app.get("/api/projects/backup")
def api_backup_project(slug: str = "") -> Response:
    """One zip of one project — screenplay, bible, references, sheets,
    boards, approvals. API keys are never included."""
    try:
        if slug:
            paths.safe_id(slug)  # traversal guard before any path math
        payload, filename = backup.make_backup(slug)
    except KeyError as e:
        raise _err(e)
    return Response(payload, media_type="application/zip",
                    headers={"Content-Disposition":
                             f'attachment; filename="{filename}"'})


@app.post("/api/projects/import/inspect")
async def api_inspect_import(file: UploadFile = File(...)) -> dict:
    """What a zip holds — read-only, writes nothing. An overwrite has to be
    describable BEFORE it is confirmed, not reported after."""
    payload = await file.read()
    try:
        return await run_in_threadpool(backup.inspect_backup, payload)
    except backup.BackupError as e:
        raise HTTPException(422, str(e))


@app.post("/api/projects/import")
async def api_import_project(file: UploadFile = File(...), slug: str = Form(""),
                             confirm_name: str = Form("")) -> dict:
    """Set an EXISTING production to the version in a backup zip. Destructive
    and confirmed by typed name, the same grammar as delete — this replaces
    the production's screenplay, library, sheets, boards and approvals."""
    if slug:
        paths.safe_id(slug)
    base = paths._project_base(slug)
    if not base.exists() or (slug and not (paths.PROJECTS_DIR / slug).is_dir()):
        raise HTTPException(404, f"unknown production: {slug}")
    name = paths._project_name(base, slug or "Untitled Production")
    if confirm_name.strip() != name:
        raise HTTPException(400, f'type the production name exactly — "{name}"')
    payload = await file.read()
    try:
        result = await run_in_threadpool(backup.import_into, slug, payload)
    except backup.BackupError as e:
        raise HTTPException(422, str(e))
    return {**result, "active": paths.ACTIVE_PROJECT,
            "was_active": slug == paths.ACTIVE_PROJECT}


@app.post("/api/projects/restore")
async def api_restore_project(file: UploadFile = File(...)) -> dict:
    """Restore a backup zip as a NEW project — existing projects are never
    touched; switch to it from the list when ready."""
    payload = await file.read()
    try:
        restored = await run_in_threadpool(backup.restore_backup, payload)
    except backup.BackupError as e:
        raise HTTPException(422, str(e))
    return {**restored, "active": paths.ACTIVE_PROJECT,
            "projects": paths.list_projects()}


def _switch_project(slug: str) -> None:
    with paths.SWITCH_LOCK:  # never interleave with the summary sweep
        paths.set_project(slug)
        paths.save_active_project(slug)
        paths.ensure_dirs()
        insights._text_cache.clear()  # screenplay cache is per-project


@app.post("/api/projects")
def api_create_project(body: dict) -> dict:
    name = str(body.get("name", "")).strip()
    if not name:
        raise HTTPException(422, "give the production a name")
    slug = "".join(c if c.isalnum() or c in "._-" else "-" for c in name).strip("-_.").lower()
    if not slug:
        raise HTTPException(422, "the name needs at least one letter or digit")
    if (paths.PROJECTS_DIR / slug).exists():
        raise HTTPException(409, f"a production already exists at: {slug}")
    d = paths.PROJECTS_DIR / slug
    d.mkdir(parents=True)
    (d / "project.json").write_text(
        json.dumps({"name": name, "created_at": store.utcnow()}, indent=2) + "\n",
        encoding="utf-8")
    _switch_project(slug)
    return {"active": paths.ACTIVE_PROJECT, "projects": paths.list_projects()}


@app.post("/api/projects/rename")
def api_rename_project(body: dict) -> dict:
    """Rename a production — the ACTIVE one unless a slug is sent (the
    library's cards rename in place). The name lives in project.json and
    shows in the header, the shelf, and the switcher."""
    name = str(body.get("name", "")).strip()
    if not name:
        raise HTTPException(422, "give the production a name")
    slug = str(body.get("slug", paths.ACTIVE_PROJECT))
    if slug:
        paths.safe_id(slug)
        if not (paths.PROJECTS_DIR / slug).is_dir():
            raise HTTPException(404, f"unknown production: {slug}")
    base = paths._project_base(slug)
    meta_path = base / "project.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    meta["name"] = name
    base.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return {"name": name, "active": paths.ACTIVE_PROJECT,
            "projects": paths.list_projects()}


@app.post("/api/projects/activate")
def api_activate_project(body: dict) -> dict:
    slug = str(body.get("slug", ""))
    try:
        if slug:
            paths.safe_id(slug)  # traversal guard before any path math
    except KeyError as e:
        raise _err(e)
    if slug and not (paths.PROJECTS_DIR / slug).is_dir():
        raise HTTPException(404, f"unknown production: {slug}")
    _switch_project(slug)
    return {"active": paths.ACTIVE_PROJECT, "projects": paths.list_projects()}


# The card reach band's stage order (PRODUCTIONS_PLAN A7). Keys are the
# app's view ids; labels are the band's Courier text.
_REACH_STAGES = (("screenplay", "01 SCRIPT"), ("wizard", "02 DESIGN"),
                 ("specs", "03 BREAKDOWN"), ("boards", "04 PANELS"),
                 ("assembly", "05 BOARDS"))
_BLOCK_STAGE = {"dashboard": "screenplay", "references": "wizard",
                "wizard": "wizard", "specs": "specs", "boards": "boards"}


def _production_row(p: dict) -> dict:
    """One production's card/switcher row, computed against the currently
    pointed paths. PRODUCTIONS_PLAN A6/A7: reach per stage, counts, the
    per-production next verb, care state."""
    blockers = insights.blocking()
    real = [b for b in blockers if b.get("kind") != "CARE"]
    ss = insights.stage_summary(blockers)
    pd, bd = ss["production_design"], ss["breakdowns"]
    pn, bo = ss["panels"], ss["boards"]

    ever = {"screenplay": bool(ss["screenplay"]), "wizard": bool(pd["bible_saved"]),
            "specs": bd["locked"] > 0, "boards": pn["approved"] > 0,
            "assembly": bo["assembled"] > 0}
    blocked = {"screenplay" if b.get("kind") == "CITE"
               else _BLOCK_STAGE.get(b.get("action", ""), "specs") for b in real}
    reach = [{"label": label,
              "state": "bad" if key in blocked else "ok" if ever[key] else "never"}
             for key, label in _REACH_STAGES]

    scenes = 0
    if ss["screenplay"]:
        try:
            scenes = sum(g.get("scenes", 0)
                         for g in insights.locations().get("locations", []))
        except Exception:
            pass
    # One board is not "1 BOARDS" (user 2026-08-07). Every count on this
    # line can legitimately be 1 — a production with one board, one panel,
    # one reference — so each carries its own plural.
    def _n(count: int, one: str, many: str = "") -> str:
        return f"{count} {one if count == 1 else (many or one + 'S')}"

    counts = (" · ".join([_n(scenes, "SCENE"), _n(pn["approved"], "PANEL"),
                          _n(bo["assembled"], "BOARD"),
                          _n(len(store.list_references()), "REF")])
              if ss["screenplay"] else "NO SCREENPLAY YET")

    # A6 — every card states its own next verb; ALL STAGES CLEAR has none.
    if not ss["screenplay"]:
        nxt = {"kicker": "DO THIS NEXT", "text": "Upload a screenplay to start the read"}
    elif not pd["bible_saved"]:
        nxt = {"kicker": "DO THIS NEXT",
               "text": "Answer the read's open questions and draft the bible"}
    elif real:
        nxt = {"kicker": "DO THIS NEXT", "text": real[0]["text"]}
    elif bd["locked"] + bd["drafts"] == 0:
        nxt = {"kicker": "DO THIS NEXT", "text": "Pick a location and create its breakdown"}
    else:
        # C1 (ratified 2026-08-01): never say "Wrapped" — the app does not
        # know principal photography finished. State only what it knows.
        last = ""
        try:
            lines = activity._log_path().read_text(encoding="utf-8").splitlines()
            if lines:
                import datetime as _dt
                d = _dt.date.fromisoformat(
                    str(json.loads(lines[-1]).get("ts", ""))[:10])
                last = f"{d.day} {d.strftime('%b').upper()}"
        except Exception:
            pass
        nxt = {"kicker": "ALL STAGES CLEAR", "clear": True,
               "text": f"NOTHING WAITING · LAST ACTIVITY {last}" if last
                       else "NOTHING WAITING"}

    # The switcher's one-line state preview (M4): where the production
    # stands, so switching is an informed move.
    holds = sum(1 for b in real if b.get("kind") == "HOLD")
    if nxt["kicker"] == "ALL STAGES CLEAR" and bo["assembled"]:
        preview = f"CLEAR · {bo['assembled']} BOARD{'S' if bo['assembled'] != 1 else ''}"
    else:
        keys = [k for k, _ in _REACH_STAGES]
        stage_no = next((i + 1 for i, r in enumerate(reach) if r["state"] == "bad"),
                        next((i + 1 for i, r in enumerate(reach) if r["state"] == "never"),
                             len(keys)))
        detail = ("NO SCREENPLAY" if not ss["screenplay"]
                  else f"{holds} HOLD{'S' if holds != 1 else ''}" if holds
                  else f"{len(real)} BLOCKED" if real
                  else f"{bd['drafts']} DRAFT{'S' if bd['drafts'] != 1 else ''}" if bd["drafts"]
                  else f"{bd['locked']} LOCKED" if bd["locked"] else "")
        preview = f"STAGE {stage_no:02d}" + (f" · {detail}" if detail else "")

    days = backup.days_since_backup(p["slug"])
    return {**p, "reach": reach, "counts": counts, "next": nxt,
            "preview": preview,
            "backup_chip": f"BACKUP {days}D" if days is not None and days >= 30 else "",
            "last_backup_at": backup.last_backup_at(p["slug"]),
            "days_since_backup": days}


@app.get("/api/projects/summary")
def api_projects_summary() -> dict:
    """One row per production for the library cards and the switcher.
    Read-only, but it points the path globals at each production in turn —
    SWITCH_LOCK makes the whole sweep atomic against switches and counter
    allocations (a render CAN be in flight while the switcher opens; the
    'single-user cannot race' assumption this once relied on was wrong)."""
    rows = []
    with paths.SWITCH_LOCK:
        original = paths.ACTIVE_PROJECT
        try:
            for p in paths.list_projects():
                paths.set_project(p["slug"])
                insights._text_cache.clear()
                try:
                    rows.append(_production_row(p))
                except Exception as e:  # one broken production never hides the shelf
                    rows.append({**p, "reach": [], "counts": "", "error": str(e)[:200],
                                 "next": {"kicker": "DO THIS NEXT",
                                          "text": f"This production failed to read: {str(e)[:120]}"}})
        finally:
            paths.set_project(original)
            insights._text_cache.clear()
    return {"active": paths.ACTIVE_PROJECT, "projects": rows}


@app.post("/api/projects/duplicate")
def api_duplicate_project(body: dict) -> dict:
    """Copy a production — everything a backup would carry, never keys.
    The copy is its own production with a fresh created_at and no backup
    history; the source is untouched."""
    import shutil
    slug = str(body.get("slug", ""))
    if slug:
        paths.safe_id(slug)
    src = paths._project_base(slug)
    if not src.exists() or (slug and not (paths.PROJECTS_DIR / slug).is_dir()):
        raise HTTPException(404, f"unknown production: {slug}")
    name = f"{paths._project_name(src, slug or 'Untitled Production')} copy"
    slug_base = "".join(c if c.isalnum() or c in "._-" else "-"
                        for c in name.lower()).strip("-_.") or "copy"
    new_slug, n = slug_base, 2
    while (paths.PROJECTS_DIR / new_slug).exists():
        new_slug = f"{slug_base}-{n}"
        n += 1
    dest = paths.PROJECTS_DIR / new_slug
    dest.mkdir(parents=True)
    for top in backup.BACKUP_DIRS:
        d = src / top
        if d.exists():
            shutil.copytree(d, dest / top,
                            ignore=shutil.ignore_patterns("settings.json"))
    meta = {"name": name, "created_at": store.utcnow(),
            "duplicated_from": slug or "(root)"}
    (dest / "project.json").write_text(json.dumps(meta, indent=2) + "\n",
                                       encoding="utf-8")
    return {"slug": new_slug, "name": name, "active": paths.ACTIVE_PROJECT,
            "projects": paths.list_projects()}


@app.post("/api/projects/delete")
def api_delete_project(body: dict) -> dict:
    """Delete a production — its screenplay, library and every board. The
    open production can never be deleted (gate stated in the UI), and the
    caller must send the production's exact name as confirmation."""
    import shutil
    slug = str(body.get("slug", ""))
    confirm = str(body.get("confirm_name", "")).strip()
    if slug:
        paths.safe_id(slug)
    base = paths._project_base(slug)
    if not base.exists() or (slug and not (paths.PROJECTS_DIR / slug).is_dir()):
        raise HTTPException(404, f"unknown production: {slug}")
    if slug == paths.ACTIVE_PROJECT:
        raise HTTPException(409, "the open production cannot be deleted — "
                                 "open another production first")
    name = paths._project_name(base, slug or "Untitled Production")
    if confirm != name:
        raise HTTPException(422, f'type the production name exactly to '
                                 f'confirm deletion: "{name}"')
    if slug:
        shutil.rmtree(base)
    else:  # the legacy root layout: remove its content dirs, never HOME
        for top in backup.BACKUP_DIRS:
            if (paths.HOME / top).exists():
                shutil.rmtree(paths.HOME / top)
        (paths.HOME / "project.json").unlink(missing_ok=True)
    return {"active": paths.ACTIVE_PROJECT, "projects": paths.list_projects()}


def _redact_secrets(o):
    """Credentials must never land in the flight recorder — any string
    field whose name smells like a secret is masked before logging."""
    if isinstance(o, dict):
        return {k: ("…REDACTED" if isinstance(v, str) and any(
            t in k.lower() for t in ("key", "secret", "token", "password"))
            else _redact_secrets(v)) for k, v in o.items()}
    if isinstance(o, list):
        return [_redact_secrets(x) for x in o]
    return o


@app.middleware("http")
async def activity_middleware(request: Request, call_next):
    """Flight recorder: every mutating /api call, with body, outcome,
    duration, and — on failure — the error detail."""
    if request.method not in ("POST", "PUT", "DELETE") or not request.url.path.startswith("/api/"):
        return await call_next(request)

    import time as _time
    ctype = request.headers.get("content-type", "")
    body_summary = None
    if "multipart" in ctype:
        body_summary = {"upload_bytes": int(request.headers.get("content-length", 0))}
        if request.query_params:
            body_summary.update(dict(request.query_params))
        req = request
    else:
        raw = await request.body()

        async def receive():
            return {"type": "http.request", "body": raw, "more_body": False}
        req = Request(request.scope, receive)
        if raw:
            try:
                body_summary = _redact_secrets(json.loads(raw))
            except json.JSONDecodeError:
                body_summary = {"raw_bytes": len(raw)}

    # Endpoints that parse multipart forms can surface their fields here via
    # request.state.activity (e.g. the repair instruction) — the middleware
    # can't read a multipart body without consuming the upload stream.
    def enrich(summary):
        extra = request.scope.get("state", {}).get("activity")
        return {**(summary or {}), **extra} if extra else summary

    t0 = _time.perf_counter()
    try:
        response = await call_next(req)
    except Exception as e:
        activity.log({"method": request.method, "path": request.url.path,
                      "body": enrich(body_summary), "status": 500, "error": str(e)[:500],
                      "ms": round((_time.perf_counter() - t0) * 1000)})
        raise
    ms = round((_time.perf_counter() - t0) * 1000)

    detail = None
    if response.status_code >= 400:
        chunks = [section async for section in response.body_iterator]
        rawresp = b"".join(chunks)
        detail = rawresp.decode(errors="replace")[:600]
        response = Response(content=rawresp, status_code=response.status_code,
                            headers=dict(response.headers),
                            media_type=response.media_type)
    activity.log({"method": request.method, "path": request.url.path,
                  "body": enrich(body_summary), "status": response.status_code,
                  **({"error": detail} if detail else {}), "ms": ms})
    return response


@app.on_event("startup")
def _collapse_legacy_revisions() -> None:
    """Revisions are retired (2026-08-16) — collapse any chain still on
    disk before the first request sees it.

    Synchronous and ahead of the variant warm: a request that arrived
    mid-migration could read a half-folded unit, and this is file moves on
    a handful of documents, not a render. The user asked for a migration,
    not a button: "we dont need UI to do this type of consolodation."
    """
    from . import revisions
    try:
        done = revisions.migrate_all_projects()
    except Exception:  # noqa: BLE001 — a boot that dies here serves nothing
        return
    for r in done:
        print(f"[migrate] {r['base']}: collapsed {', '.join(r['collapsed'])} "
              f"({r['files_moved']} take file(s) folded)", flush=True)
    _fold_touchstones_everywhere()


@app.on_event("startup")
def _warm_display_variants() -> None:
    """Pre-build the back-catalogue's display variants in the background at boot,
    so a cold board never triggers a storm of synchronous 4K resizes on first
    view (user 2026-08-09 — dozens at once saturated a tenant). Non-blocking,
    capped in imaging, best-effort; the lazy path stays as the backstop."""
    import threading

    def _run():
        try:
            generate.warm_all_candidates()
            store.warm_all_references()
        except Exception:
            pass
    threading.Thread(target=_run, name="variant-warm", daemon=True).start()


def _err(exc: Exception) -> HTTPException:
    codes = {KeyError: 404, FileExistsError: 409, PermissionError: 423, ValueError: 422}
    return HTTPException(status_code=codes.get(type(exc), 500), detail=str(exc))


# ------------------------------------------------------------------ dashboard

@app.get("/api/state")
def api_state() -> dict:
    app_state = store.load_app_state()
    refs = store.list_references()
    specs = store.list_specs()
    project_state = {}
    if paths.PROJECT_STATE.exists():
        project_state = json.loads(paths.PROJECT_STATE.read_text(encoding="utf-8"))

    missing = []
    if not app_state.get("screenplay"):
        missing.append("Screenplay not uploaded")
    if not any(r["role"] == "BOARD_LAYOUT_STYLE" and r["status"] == "APPROVED"
               for r in refs):
        missing.append("Master Board #001 (BOARD_LAYOUT_STYLE) not approved in reference library")

    blockers = insights.blocking()
    summary = insights.stage_summary(blockers)
    return {
        # The active production's name — never hardcoded.
        "project": paths._project_name(
            paths._project_base(paths.ACTIVE_PROJECT), "Untitled Production"),
        "screenplay": app_state.get("screenplay"),
        "references": {
            "total": len(refs),
            "approved": sum(1 for r in refs if r["status"] == "APPROVED"),
            "provisional": sum(1 for r in refs if r["status"] == "PROVISIONAL"),
            "rejected": sum(1 for r in refs if r["status"] == "REJECTED"),
        },
        "specs": specs,
        "prohibited_inventions": project_state.get("prohibited_inventions", []),
        "missing_dependencies": missing,
        "blocking": blockers,
        "stage_summary": summary,
        "next": insights.next_verb(summary, blockers),
        "suggested_roles": store.SUGGESTED_ROLES,
    }


@app.get("/api/activity")
def api_activity(limit: int = 10) -> list[dict]:
    """The flight recorder, phrased for humans — newest first."""
    return insights.recent_activity(max(1, min(int(limit), 50)))


# ----------------------------------------------------------------- screenplay

@app.post("/api/screenplay")
async def api_upload_screenplay(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    if not content:
        raise HTTPException(422, "empty file")
    record = store.set_screenplay(file.filename or "screenplay.pdf", content)
    # Re-search every quoted evidence citation in the new draft. Report-only:
    # specs are never auto-mutated — broken citations surface as blockers.
    if store.list_specs():
        try:
            report = await run_in_threadpool(insights.citation_check)
            record["citation_check"] = {
                "quotes_checked": report.get("quotes_checked", 0),
                "missing": len(report.get("missing", [])),
            }
        except Exception:
            pass  # the upload must never fail because the audit hiccuped
    return record


@app.get("/api/screenplay/locations")
def api_screenplay_locations() -> dict:
    """Deterministic slugline coverage map — see insights.locations()."""
    return insights.locations()


@app.get("/api/screenplay/text")
def api_screenplay_text() -> dict:
    """The current draft's extracted text, for the in-app reading view."""
    text = insights.screenplay_text()
    return {"available": bool(text.strip()), "text": text}


@app.get("/api/screenplay/file")
def api_screenplay_file():
    """The original uploaded file, served inline for the user to read.
    The pipeline never consumes this — models get the extracted text."""
    rec = store.load_app_state().get("screenplay")
    if not rec:
        raise HTTPException(404, "no screenplay uploaded")
    p = paths.SCREENPLAY_DIR / rec["file"]
    if not p.exists():
        raise HTTPException(404, f"screenplay file missing on disk: {rec['file']}")
    return FileResponse(p, filename=rec["file"],
                        content_disposition_type="inline")


@app.get("/api/screenplay/keywords")
def api_screenplay_keywords(name: str = "") -> dict:
    """Trigger words for a design language, derived deterministically from
    the screenplay — see insights.derive_keywords()."""
    if not name.strip():
        raise HTTPException(422, "name is required")
    return insights.derive_keywords(name.strip())


@app.get("/api/screenplay/citation-report")
def api_citation_report() -> dict:
    return insights.load_citation_report() or {"available": False,
                                               "missing": []}


# ----------------------------------------------------------------- references

@app.get("/api/references")
def api_list_references() -> list[dict]:
    refs = store.list_references()
    usage = insights.reference_usage()
    for r in refs:
        r["used_in"] = usage.get(r["id"], 0)
    return refs


@app.post("/api/references")
async def api_add_reference(
    file: UploadFile = File(...),
    role: str = Form(...),
    controls: str = Form(""),
    does_not_control: str = Form(""),
    notes: str = Form(""),
) -> dict:
    content = await file.read()
    if not content:
        raise HTTPException(422, "empty file")
    split = lambda s: [x.strip() for x in s.split(",") if x.strip()]
    try:
        return store.add_reference(file.filename or "reference.png", content,
                                   role, split(controls), split(does_not_control), notes)
    except ValueError as e:
        raise _err(e)


@app.post("/api/references/swatch")
async def api_add_swatch(body: dict) -> dict:
    """NON-CANON (2026-08-05, D8-ratified): a swatch reference — pure
    solid color (or a value-key pair, two halves), rendered locally at
    zero cost. No text in the pixels; name/hex/citation ride the notes."""
    from . import wizard

    hexv = wizard._clean_hex(body.get("hex"))
    if not hexv:
        raise HTTPException(422, "hex must look like #8A4B2E")
    pair = wizard._clean_hex(body.get("pair_hex")) or None
    name = str(body.get("name") or f"SWATCH {hexv}").strip()[:48].upper()
    # A label, not a paragraph — same rule the proposals follow.
    cite = wizard.short_cite(body.get("cite"))
    notes = " · ".join(x for x in
                       [name, hexv + (f" / {pair}" if pair else ""), cite] if x)
    try:
        ref = store.add_reference(f"{name.lower().replace(' ', '-')}.png",
                                  wizard.render_swatch_png(hexv, pair),
                                  "COLOR_PALETTE", [], [], notes,
                                  source="swatch-manual")
    except ValueError as e:
        raise _err(e)
    if body.get("approve"):
        ref = store.set_reference_status(ref["id"], "APPROVED")
    return ref


@app.post("/api/references/{ref_id}/swatch")
async def api_recolor_swatch(ref_id: str, body: dict) -> dict:
    """Repaint an existing swatch in place (user 2026-08-06). The reference
    keeps its id, name and review state — only its pixels change."""
    from . import wizard

    try:
        return await run_in_threadpool(
            wizard.recolor_swatch, ref_id, body.get("hex"), body.get("pair_hex"))
    except KeyError:
        raise HTTPException(404, f"unknown reference: {ref_id}")
    except autofill.AutofillError as e:
        raise HTTPException(422, str(e))
    except ValueError as e:
        raise _err(e)


@app.post("/api/references/{ref_id}/hero")
async def api_set_swatch_hero(ref_id: str) -> dict:
    """Name this swatch the hero of its design language — the colour
    splashed through that faction's sets. Single-valued: setting it clears
    the previous hero in the same language (PALETTE_GROUPS_PLAN §4)."""
    from . import wizard

    try:
        return await run_in_threadpool(wizard.set_hero, ref_id)
    except KeyError:
        raise HTTPException(404, f"unknown reference: {ref_id}")
    except autofill.AutofillError as e:
        raise HTTPException(400, str(e))


@app.post("/api/wizard/swatches")
async def api_wizard_swatches(body: dict) -> dict:
    """Bible-cited palette proposals (NON-CANON widget) — proposals only;
    each approval lands through /api/references/swatch."""
    langs = [str(x).strip() for x in (body.get("languages") or []) if str(x).strip()]
    try:
        return await run_in_threadpool(
            wizard.generate_swatches, str(body.get("provider") or "gemini"),
            langs or None, str(body.get("note") or ""), bool(body.get("deep")))
    except autofill.AutofillError as e:
        raise HTTPException(409, str(e))


@app.patch("/api/references/{ref_id}")
async def api_update_reference(ref_id: str, fields: dict) -> dict:
    try:
        return store.update_reference(ref_id, fields)
    except (KeyError, PermissionError) as e:
        raise _err(e)


@app.post("/api/references/{ref_id}/status")
async def api_reference_status(ref_id: str, body: dict) -> dict:
    try:
        return store.set_reference_status(ref_id, body.get("status", ""),
                                          body.get("reason", ""))
    except (KeyError, ValueError) as e:
        raise _err(e)


@app.delete("/api/references/{ref_id}")
def api_delete_reference(ref_id: str) -> dict:
    try:
        return store.delete_reference(ref_id)
    except KeyError as e:
        raise _err(e)


@app.get("/api/references/{ref_id}/image")
def api_reference_image(ref_id: str, size: str = "full", thumb: bool = False):
    p = store.reference_image_path(ref_id, size=size, thumb=thumb)
    if p is None:
        raise HTTPException(404, f"no image for {ref_id}")
    return FileResponse(p)


# ---------------------------------------------------------------------- specs

@app.get("/api/specs")
def api_list_specs() -> list[dict]:
    return store.list_specs()


def _require_production_design() -> None:
    """Breakdowns draw their rendering language, environments and subjects
    from the Art Direction Bible — without it a sheet has nothing to draw
    from. 423: the resource is locked by an unmet upstream condition (the
    UI states this gate before it is ever hit)."""
    if not bible.load_text().strip():
        raise HTTPException(423, "production design incomplete — save the "
                                 "Art Direction Bible before drafting "
                                 "breakdowns")


@app.post("/api/specs")
async def api_new_spec(body: dict) -> dict:
    _require_production_design()
    try:
        return store.new_spec(body["specification_id"].strip(),
                              body.get("subject", "").strip(),
                              body.get("mode", "CANON_EXTRACTION"),
                              body.get("board_type", "LOCATION"))
    except (KeyError, ValueError, FileExistsError) as e:
        raise _err(e)


@app.get("/api/specs/{spec_id}")
def api_get_spec(spec_id: str) -> dict:
    spec = store.get_spec(spec_id)
    if spec is None:
        raise HTTPException(404, f"unknown specification: {spec_id}")
    hay = " ".join(str(x) for x in
                   [spec.get("subject", ""), spec.get("render_intent", "")]
                   + [f"{p.get('title', '')} {p.get('purpose', '')} "
                      f"{' '.join(p.get('required_objects', []))}"
                      for p in spec.get("panels", [])])
    return {"spec": spec, "locked": store.spec_locked(spec_id),
            "lock_hash": store.spec_lock_hash(spec_id),
            "bible_catalog": bible.sections_catalog(),
            "bible_inferred": bible.infer_selection(hay)}


@app.put("/api/specs/{spec_id}")
async def api_save_spec(spec_id: str, spec: dict) -> dict:
    try:
        return store.save_spec(spec_id, spec)
    except (KeyError, ValueError, PermissionError) as e:
        raise _err(e)


@app.post("/api/specs/{spec_id}/validate")
def api_validate_spec(spec_id: str) -> dict:
    spec = store.get_spec(spec_id)
    if spec is None:
        raise HTTPException(404, f"unknown specification: {spec_id}")
    return check_spec(spec)


@app.post("/api/specs/{spec_id}/approve")
def api_approve_spec(spec_id: str) -> dict:
    try:
        return store.approve_spec(spec_id, full_validate)
    except (KeyError, ValueError, PermissionError) as e:
        raise _err(e)


@app.post("/api/specs/{spec_id}/revise")
async def api_revise_spec(spec_id: str, request: Request) -> dict:
    """Clone into the next revision. Body may carry {"revise_panels":
    ["P01", ...]} — the panels being revised; the rest are carried
    read-only and keep feeding the unit's board. No body = all revised
    (legacy behavior)."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        return store.revise_spec(spec_id, (body or {}).get("revise_panels"))
    except (KeyError, FileExistsError) as e:
        raise _err(e)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/revision-scope")
def api_upgrade_revision_panel(spec_id: str, body: dict) -> dict:
    """'Also revise this panel' — a carried panel joins the draft
    revision. One-way, journaled."""
    try:
        return store.upgrade_revision_panel(spec_id,
                                            str(body.get("panel_id", "")))
    except KeyError as e:
        raise _err(e)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.put("/api/specs/{spec_id}/board-keeps/{panel_id}")
def api_set_board_keep(spec_id: str, panel_id: str, body: dict) -> dict:
    """The KEEP act: seat a below-floor approved take on the unit's board
    anyway — explicit and journaled; the slot stops asking."""
    from . import revisions
    try:
        return revisions.set_keep(revisions.base_of(spec_id), panel_id,
                                  str(body.get("candidate_id", "")))
    except KeyError as e:
        raise _err(e)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.delete("/api/specs/{spec_id}/board-keeps/{panel_id}")
def api_clear_board_keep(spec_id: str, panel_id: str) -> dict:
    from . import revisions
    try:
        return revisions.clear_keep(revisions.base_of(spec_id), panel_id)
    except KeyError as e:
        raise _err(e)


@app.get("/api/specs/{spec_id}/revisions")
def api_list_revisions(spec_id: str) -> dict:
    """The unit's revision family — feeds the boards-stage base picker
    and the FROM R(n) provenance chips."""
    from . import revisions
    base, structure = revisions.resolve_board_id(spec_id)
    out = []
    for rid in revisions.revisions_of(base):
        s = store.get_spec(rid) or {}
        out.append({"specification_id": rid,
                    "revision": revisions.revision_of(rid),
                    "status": s.get("status", ""),
                    "locked": store.spec_locked(rid),
                    "revision_scope": s.get("revision_scope")})
    return {"base": base, "structure_spec_id": structure, "revisions": out}


@app.get("/api/specs/{spec_id}/consolidation")
def api_consolidation_plan(spec_id: str) -> dict:
    """What collapsing this unit into one breakdown would do — read before
    the act, so the consequence is state rather than an after-the-fact
    report."""
    from . import revisions
    return revisions.consolidation_plan(spec_id)


@app.post("/api/specs/{spec_id}/consolidate")
def api_consolidate(spec_id: str) -> dict:
    """Collapse a revision chain into one breakdown (user ruling
    2026-08-16). Revisions are retired; this is the migration off them."""
    from . import revisions
    try:
        return revisions.consolidate(spec_id)
    except KeyError as e:
        raise _err(e)
    except (ValueError, FileExistsError) as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/unlock")
def api_unlock_spec(spec_id: str) -> dict:
    try:
        return store.unlock_spec(spec_id)
    except (KeyError, ValueError, PermissionError) as e:
        raise _err(e)


@app.delete("/api/specs/{spec_id}")
def api_delete_spec(spec_id: str) -> dict:
    try:
        return store.delete_spec(spec_id)
    except (KeyError, PermissionError) as e:
        raise _err(e)


# ----------------------------------------------------------------- settings

@app.get("/api/settings")
def api_get_settings() -> dict:
    import os
    s = generate.load_settings()
    gkey = s.get("gemini_api_key", "")
    okey = s.get("openai_api_key", "")
    genv = os.environ.get("GEMINI_API_KEY", "").strip()
    oenv = os.environ.get("OPENAI_API_KEY", "").strip()
    tests = s.get("engine_tests", {})
    # Honest status only: "configured" states where a key came from;
    # "last_test" is the persisted outcome of the user's own Test click —
    # never a fake CONNECTED.
    gemini_src = "settings" if gkey else ("env" if genv else None)
    openai_src = "settings" if okey else ("env" if oenv else None)
    engines = {
        "gemini": {"configured": bool(gemini_src), "source": gemini_src,
                   "last_test": tests.get("gemini")},
        "openai": {"configured": bool(openai_src), "source": openai_src,
                   "last_test": tests.get("openai")},
        "openai-chat": {"configured": bool(openai_src), "source": openai_src,
                        "last_test": tests.get("openai-chat")},
    }
    if generate.mock_enabled():  # implies debug_tools_enabled()
        # The debug dry-run engine: always "configured" while the toggle is
        # on — it has no key and no test because it never calls anything.
        engines["mock"] = {"configured": True, "source": "debug",
                           "last_test": None}
    customs = []
    for e in generate.custom_engines():
        pid = f"custom:{e['id']}"
        engines[pid] = {"configured": True, "source": "settings",
                        "last_test": tests.get(pid)}
        customs.append({"id": e["id"], "label": e.get("label") or e["id"],
                        "model": e["model"], "base_url": e.get("base_url", ""),
                        "key_hint": f"…{e['api_key'][-4:]}"})
    akey = s.get("anthropic_api_key", "")
    if akey:
        # Narrative credential (F6 backend now live): same honest-status
        # grammar as the image engines.
        engines["anthropic"] = {"configured": True, "source": "settings",
                                "last_test": tests.get("anthropic")}
    from . import narrative
    provider_meta = generate.all_providers()
    return {"openai_env_key_hint": f"…{oenv[-4:]}" if oenv else None,
            "anthropic_api_key_set": bool(akey),
            "anthropic_api_key_hint": f"…{akey[-4:]}" if akey else None,
            "gemini_api_key_set": bool(gkey),
            "gemini_api_key_hint": f"…{gkey[-4:]}" if gkey else None,
            "openai_api_key_set": bool(okey),
            "openai_api_key_hint": f"…{okey[-4:]}" if okey else None,
            "model": generate.MODEL,
            "openai_model": generate.OPENAI_MODEL,
            "openai_chat_model": generate._chat_model(),
            "openai_chat_model_default": generate.OPENAI_CHAT_MODEL,
            "providers": {k: v["label"] for k, v in provider_meta.items()},
            "provider_meta": provider_meta,
            "aspects": generate.aspect_catalog(),
            "board_templates": store.BOARD_TEMPLATES,
            "custom_engines": customs,
            "debug_tools": generate.debug_tools_enabled(),
            "default_provider": generate.DEFAULT_PROVIDER,
            "preferred_provider": generate.preferred_provider(),
            "narrative_provider": (s.get("narrative_provider") or "openai"),
            "anthropic_model": narrative.anthropic_model(),
            "openrouter_narrative_ready": narrative.usable("openrouter"),
            "openrouter_narrative_model": narrative.OPENROUTER_NARRATIVE_MODEL,
            "roles": _role_states(engines),
            "engines": engines}


def _role_states(engines: dict) -> dict:
    """One state per AI role for the header marks (C8): the worst state
    among everything that role needs. ok / warn (degraded, still runs) /
    bad (blocked) / none (not configured)."""
    def key_state(e):
        if not e or not e.get("configured"):
            return "none"
        t = e.get("last_test")
        if t and t.get("ok") is False:
            return "bad"
        if t and t.get("ok"):
            return "ok"
        return "warn"  # configured but never proven by a test

    narrative = key_state(engines.get("openai"))

    image_states = [key_state(engines[k]) for k in engines]
    for row in (connectors.connector_public(cid) for cid in connectors.REGISTRY):
        if row["enabled_count"] == 0 and row["status"] == "NOT_CONNECTED":
            continue
        image_states.append({"SYNCED": "ok", "REJECTED": "bad",
                             "NO_NETWORK": "warn",
                             "NOT_CONNECTED": "bad"}[row["status"]])
    live = [s for s in image_states if s != "none"]
    if not live:
        image = "none"
    elif "ok" in live:
        image = "ok" if "bad" not in live and "warn" not in live else "warn"
    else:
        image = "bad"
    return {"narrative": narrative, "image": image}


@app.post("/api/settings")
async def api_save_settings(body: dict) -> dict:
    s = generate.load_settings()
    if "gemini_api_key" in body:
        s["gemini_api_key"] = str(body["gemini_api_key"]).strip()
    if "openai_api_key" in body:
        s["openai_api_key"] = str(body["openai_api_key"]).strip()
    if "anthropic_api_key" in body:
        # F6 backend live: the key now powers the narrative role directly.
        s["anthropic_api_key"] = str(body["anthropic_api_key"]).strip()
    if "narrative_provider" in body:
        p = str(body["narrative_provider"]).strip()
        if p not in {"openai", "gemini", "anthropic", "openrouter"}:
            raise HTTPException(422, f"unknown narrative provider: {p}")
        s["narrative_provider"] = p
    if "debug_mock" in body:
        if not generate.debug_tools_enabled():
            raise HTTPException(404)  # the feature does not exist here
        s["debug_mock"] = bool(body["debug_mock"])
        # Turning the dry-run engine off must never leave it selected.
        if not s["debug_mock"] and s.get("preferred_provider") == "mock":
            s["preferred_provider"] = generate.DEFAULT_PROVIDER
    if "preferred_provider" in body:
        p = str(body["preferred_provider"]).strip()
        if p not in generate.all_providers():
            raise HTTPException(422, f"unknown provider: {p}")
        s["preferred_provider"] = p
    if "openai_chat_model" in body:
        # Role 01's selection — empty string returns to the default.
        s["openai_chat_model"] = str(body["openai_chat_model"]).strip()
    generate.save_settings(s)
    return api_get_settings()


# ---------------------------------------------------------------- connectors
# CONNECTORS_PLAN N3/N4: state rows, key save + sync, refresh, disconnect,
# enable/disable, the catalog for browser and picker, OpenRouter PKCE.
# Every failure is a stated row condition, never a bare 500; a failing
# connector never silently reroutes a render.

@app.get("/api/connectors")
def api_connectors_state() -> dict:
    return {"connectors": [connectors.connector_public(cid)
                           for cid in connectors.REGISTRY],
            "stats": connectors.stats()}


@app.post("/api/connectors/{cid}/key")
def api_connector_key(cid: str, body: dict = Body(...)) -> dict:
    if cid not in connectors.REGISTRY:
        raise HTTPException(404)
    key = str(body.get("key", "")).strip()
    if not key:
        raise HTTPException(422, "key required")
    try:
        return connectors.save_key(cid, key)
    except connectors.ConnectorError as e:
        raise HTTPException(422, str(e))


@app.post("/api/connectors/{cid}/refresh")
def api_connector_refresh(cid: str) -> dict:
    if cid not in connectors.REGISTRY:
        raise HTTPException(404)
    try:
        return connectors.sync(cid)
    except connectors.ConnectorError as e:
        raise HTTPException(422, str(e))


@app.post("/api/connectors/{cid}/disconnect")
def api_connector_disconnect(cid: str) -> dict:
    if cid not in connectors.REGISTRY:
        raise HTTPException(404)
    connectors.disconnect(cid)
    return connectors.connector_public(cid)


@app.post("/api/connectors/enable")
def api_connector_enable(body: dict = Body(...)) -> dict:
    mid = str(body.get("id", ""))
    try:
        return connectors.set_enabled(mid, bool(body.get("on")))
    except connectors.ConnectorError:
        # A server-side search hit the cache has never seen: the client
        # sends the record along; adopt it, then enable.
        rec = body.get("record")
        if not (isinstance(rec, dict) and rec.get("id") == mid):
            raise HTTPException(422, f"unknown catalog model: {mid}")
        try:
            connectors.adopt_record(rec)
            return connectors.set_enabled(mid, bool(body.get("on")))
        except connectors.ConnectorError as e:
            raise HTTPException(422, str(e))


@app.get("/api/connectors/catalog")
def api_connectors_catalog(q: str = "", refs: bool = False, fourk: bool = False,
                           priced: bool = False, scope: str = "all") -> dict:
    records = (connectors.enabled_records() if scope == "enabled"
               else connectors.catalog_records())
    hits = connectors.filter_records(records, query=q, refs_only=refs,
                                     fourk_only=fourk, priced_only=priced)
    searched = "enabled models" if scope == "enabled" else "the synced catalogs"
    # The field never returns "no results" while results exist upstream
    # (C7): a miss with a query escalates to fal's server-side search.
    if q and scope == "all" and not hits:
        fal_pub = connectors.connector_public("fal")
        if fal_pub["status"] == "SYNCED":
            key = connectors.load_state().get("fal", {}).get("key", "")
            try:
                server = connectors.fal_search(key, q)
                known = {m["id"] for m in records}
                hits = connectors.filter_records(
                    [m for m in server if m["id"] not in known],
                    refs_only=refs, fourk_only=fourk, priced_only=priced)
                searched = "the synced catalogs and fal's live catalog"
            except Exception:
                searched = "the synced catalogs (fal unreachable — cache only)"
    return {"records": hits, "total": len(records), "searched": searched}


# C6 — the witnessed test frame: one standardised in-house prompt through
# the user's own key; the result becomes the model's preview — our
# witnessed output, never the vendor's marketing sample. Cached to disk,
# served from disk, works air-gapped afterward.
_PREVIEW_PROMPT = (
    "Production still, working film set at dusk: a practical interior "
    "location with visible light rigging, one crew member adjusting a "
    "flag on a C-stand, honest colour, shallow depth of field, no text, "
    "no watermark, no logo.")


@app.post("/api/connectors/preview")
def api_connector_preview(body: dict = Body(...)) -> dict:
    import re as _re
    mid = str(body.get("id", ""))
    rec = next((m for m in connectors.enabled_records() if m["id"] == mid), None)
    if rec is None:
        raise HTTPException(404, "enable the model first")
    connectors.cache_dir().mkdir(parents=True, exist_ok=True)
    name = _re.sub(r"[^A-Za-z0-9._-]", "_", mid) + ".png"
    out = connectors.cache_dir() / name
    try:
        generate._render_connector(mid, _PREVIEW_PROMPT, [], "1K", "3:2", out)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    state = connectors.load_state()
    state.setdefault(rec["connector"], {}).setdefault("previews", {})[mid] = name
    connectors.save_state(state)
    return {"id": mid, "preview": f"/api/connectors/preview-image/{name}"}


@app.get("/api/connectors/preview-image/{name}")
def api_connector_preview_image(name: str):
    p = connectors.cache_dir() / paths.safe_id(name)
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="image/png")


@app.get("/api/connectors/openrouter/auth")
def api_openrouter_auth(request: Request) -> dict:
    # The callback must name the address the BROWSER is on — behind the
    # cloud studio's wildcard router that is X-Forwarded-Host (set by our
    # proxy, which strips any inbound copy), never request.base_url
    # (the internal railway host, where the session cookie doesn't live).
    fwd_host = request.headers.get("x-forwarded-host", "").strip()
    base = f"https://{fwd_host}" if fwd_host else str(request.base_url).rstrip("/")
    return {"url": connectors.pkce_start(base + "/connectors/openrouter/callback")}


@app.get("/connectors/openrouter/callback")
def api_openrouter_callback(code: str = ""):
    try:
        connectors.pkce_finish(code)
    except Exception as e:
        return HTMLResponse(
            "<pre>OpenRouter connect did not complete: "
            f"{str(e)[:300]}\n\nReturn to the app and start again from "
            "Settings → AI &amp; engines.</pre>", status_code=400)
    # F3 — the notice's promise: connecting sets the recommended defaults.
    # gpt-image-2 via OpenRouter becomes the enabled starting engine (the
    # narrative default is already gpt-5.6). A courtesy, never a failure.
    try:
        target = "or:openai/gpt-image-2"
        if any(m["id"] == target for m in connectors.catalog_records()):
            connectors.set_enabled(target, True)
            s = generate.load_settings()
            if not s.get("preferred_provider"):
                s["preferred_provider"] = target
                generate.save_settings(s)
    except Exception:
        pass
    # The app restores the last view (Settings) on load.
    return RedirectResponse("/", status_code=303)


# -------------------------------------------------- debug: page-text edits
# Debug tool (user request 2026-08-03): rewrite any static UI text in
# place. Overrides are exact-text → replacement pairs, install-level (they
# are workbench copy, not production data — never in backups), applied
# client-side after every render.

def _text_overrides_path():
    return paths.HOME / "text_overrides.json"


def _require_debug_tools() -> None:
    if not generate.debug_tools_enabled():
        raise HTTPException(404)


@app.get("/api/debug/text-overrides")
def api_get_text_overrides() -> dict:
    _require_debug_tools()
    p = _text_overrides_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except json.JSONDecodeError:
        data = {}
    return {"overrides": data if isinstance(data, dict) else {}}


@app.put("/api/debug/text-overrides")
async def api_put_text_overrides(body: dict) -> dict:
    _require_debug_tools()
    overrides = body.get("overrides")
    if not isinstance(overrides, dict):
        raise HTTPException(422, "overrides must be an object of text → text")
    clean = {str(k)[:500]: str(v)[:500] for k, v in overrides.items()
             if str(k).strip()}
    store._atomic_write_json(_text_overrides_path(), clean)
    return {"overrides": clean}


@app.delete("/api/debug/text-overrides")
def api_clear_text_overrides() -> dict:
    _require_debug_tools()
    _text_overrides_path().unlink(missing_ok=True)
    return {"overrides": {}}


@app.post("/api/settings/engines")
async def api_add_engine(body: dict) -> dict:
    """Add a user-owned image engine. Contract: the endpoint must speak the
    OpenAI Images API (images.generate / images.edit) at base_url."""
    import re as _re
    label = str(body.get("label", "")).strip()
    base_url = str(body.get("base_url", "")).strip()
    model = str(body.get("model", "")).strip()
    api_key = str(body.get("api_key", "")).strip()
    if not (label and base_url and model and api_key):
        raise HTTPException(422, "label, base_url, model, and api_key are all required")
    if not base_url.startswith(("http://", "https://")):
        raise HTTPException(422, "base_url must start with http:// or https://")
    eid = _re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "engine"
    s = generate.load_settings()
    engines = s.get("custom_engines", [])
    if any(e.get("id") == eid for e in engines):
        raise HTTPException(409, f"an engine named '{eid}' already exists — remove it first")
    engines.append({"id": eid, "label": label, "base_url": base_url,
                    "model": model, "api_key": api_key})
    s["custom_engines"] = engines
    generate.save_settings(s)
    return api_get_settings()


@app.delete("/api/settings/engines/{eid}")
def api_delete_engine(eid: str) -> dict:
    s = generate.load_settings()
    engines = s.get("custom_engines", [])
    if not any(e.get("id") == eid for e in engines):
        raise HTTPException(404, f"no custom engine '{eid}'")
    s["custom_engines"] = [e for e in engines if e.get("id") != eid]
    if s.get("preferred_provider") == f"custom:{eid}":
        s["preferred_provider"] = generate.DEFAULT_PROVIDER
    s.get("engine_tests", {}).pop(f"custom:{eid}", None)
    generate.save_settings(s)
    return api_get_settings()


def _record_engine_test(provider: str, ok: bool, detail: str = "") -> None:
    s = generate.load_settings()
    tests = s.get("engine_tests", {})
    tests[provider] = {"ok": ok, "at": store.utcnow(),
                       **({"detail": detail[:200]} if detail else {})}
    s["engine_tests"] = tests
    generate.save_settings(s)


@app.post("/api/settings/test")
async def api_test_settings(body: dict = None) -> dict:
    provider = (body or {}).get("provider", generate.DEFAULT_PROVIDER)
    try:
        result = await run_in_threadpool(generate.test_connection, provider)
    except generate.GenerationError as e:
        _record_engine_test(provider, False, str(e))
        raise HTTPException(422, str(e))
    except Exception as e:
        _record_engine_test(provider, False, str(e))
        raise HTTPException(502, f"{provider} connection failed: {e}")
    _record_engine_test(provider, True)
    return result


# --------------------------------------------------------------- generation

@app.get("/api/specs/{spec_id}/panels/{panel_id}/prompt")
def api_panel_prompt(spec_id: str, panel_id: str, refs: str = "") -> dict:
    ref_ids = [r for r in refs.split(",") if r]
    try:
        spec, panel, ref_records = generate._resolve_generation_inputs(
            spec_id, panel_id, ref_ids)
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    return {"prompt": generate.compile_panel_prompt(spec, panel, ref_records)}


@app.post("/api/specs/{spec_id}/panels")
def api_add_panel(spec_id: str, body: dict) -> dict:
    """Add a panel to a sheet from the panels workbench — appended as a work
    order, the lock re-stamped (same controlled edit as a between-takes brief
    change). See store.add_panel."""
    try:
        return store.add_panel(spec_id, str(body.get("title", "")),
                               str(body.get("purpose", "")))
    except KeyError as e:
        raise _err(e)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.get("/api/camera-defaults")
def api_get_camera_defaults() -> dict:
    """The production's default camera grammar (Art Direction Bible level)."""
    return store.camera_defaults()


@app.post("/api/camera-defaults")
def api_save_camera_defaults(body: dict) -> dict:
    try:
        return store.save_camera_defaults(body or {})
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/panels/{panel_id}/camera")
def api_amend_panel_camera(spec_id: str, panel_id: str, body: dict) -> dict:
    """Set a panel's camera between takes — journaled, lock re-stamped; refused
    only when this panel already has approved canon output. See
    store.amend_panel_camera."""
    try:
        return store.amend_panel_camera(spec_id, panel_id, body or {})
    except (KeyError, PermissionError) as e:
        raise _err(e)
    except ValueError as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/panels/{panel_id}/purpose")
def api_amend_panel_purpose(spec_id: str, panel_id: str, body: dict) -> dict:
    """The workbench's between-takes brief edit — journaled, lock re-stamped;
    refused only when this panel already has approved canon output."""
    try:
        return store.amend_panel_purpose(
            spec_id, panel_id, str(body.get("purpose", "")))
    except (KeyError, PermissionError, ValueError) as e:
        raise _err(e)


@app.post("/api/specs/{spec_id}/panels/{panel_id}/generate")
async def api_generate_panel(spec_id: str, panel_id: str, body: dict) -> dict:
    try:
        return await run_in_threadpool(
            generate.generate_panel, spec_id, panel_id,
            body.get("ref_ids", []),
            body.get("image_size", "2K"),
            body.get("aspect_ratio", "16:9"),
            body.get("provider") or generate.preferred_provider(),
            body.get("render_prompt", ""))
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"generation failed: {e}")


@app.post("/api/specs/{spec_id}/panels/{panel_id}/draft-prose")
async def api_draft_prose(spec_id: str, panel_id: str, body: dict) -> dict:
    try:
        return await run_in_threadpool(
            generate.draft_render_prose, spec_id, panel_id, body.get("ref_ids", []))
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"prose draft failed: {e}")


@app.post("/api/specs/{spec_id}/panels/{panel_id}/composition-check")
async def api_composition_check(spec_id: str, panel_id: str, body: dict) -> dict:
    """Pre-render, text-only, advisory: the screenplay scene is re-derived
    and the compiled prompt judged against it — no image spend, nothing
    persisted. See app/composition.py."""
    try:
        return await run_in_threadpool(
            composition.check_panel, spec_id, panel_id,
            body.get("ref_ids", []), str(body.get("provider") or ""))
    except KeyError as e:
        raise _err(e)
    except (autofill.AutofillError, generate.GenerationError) as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"composition check failed: {e}")


@app.get("/api/specs/{spec_id}/candidates")
def api_list_candidates(spec_id: str, scope: str = "") -> list[dict]:
    """One revision's takes by default; ?scope=base aggregates the whole
    unit — ordered revision-major, oldest first, each row annotated
    spec_id + revision, so a newest-wins fold over the list is correct
    (one board per unit, 2026-08-13)."""
    if scope != "base":
        return generate.list_candidates(spec_id)
    from . import revisions
    out = []
    for rid in revisions.revisions_of(revisions.base_of(spec_id)):
        for c in generate.list_candidates(rid):
            out.append({**c, "spec_id": rid,
                        "revision": revisions.revision_of(rid)})
    return out


@app.get("/api/specs/{spec_id}/carried-feedback")
def api_carried_feedback(spec_id: str) -> dict:
    """Every rejection note that carries into this spec's future prompts —
    live rejected takes and the archive rows deleted takes left behind.
    The rail renders this list, so visibility equals reality."""
    return {"items": generate.carried_feedback(spec_id)}


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/feedback-edit")
def api_edit_feedback(spec_id: str, cand_id: str, body: dict) -> dict:
    """Rewrite a rejection note in place (live record or archive row) —
    journaled; the note keeps carrying with its new words."""
    try:
        return generate.edit_feedback(spec_id, cand_id,
                                      str(body.get("reason", "")))
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/feedback-delete")
def api_delete_feedback(spec_id: str, cand_id: str) -> dict:
    """Remove a rejection note from every future prompt — an explicit,
    logged user act (2026-08-13 ruling: notes are destroyed only by their
    own Delete verb, never as a side effect)."""
    try:
        return generate.delete_feedback(spec_id, cand_id)
    except KeyError as e:
        raise _err(e)


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/correction-intake")
async def api_correction_intake(spec_id: str, cand_id: str, body: dict) -> dict:
    """Parse a rejection into proposed structural deltas (camera, require,
    forbid, brief extension) stored on the candidate record. Proposals
    only — applying is a separate, user-driven call."""
    from . import corrections
    try:
        return await run_in_threadpool(
            corrections.propose, spec_id, cand_id,
            str(body.get("provider") or ""))
    except KeyError as e:
        raise _err(e)
    except (autofill.AutofillError, generate.GenerationError) as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"correction intake failed: {e}")


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/correction-intake/apply")
def api_correction_apply(spec_id: str, cand_id: str, body: dict) -> dict:
    """Apply selected proposed deltas through the journaled controlled-edit
    doors (amend_panel_camera / amend_panel_content). An approved take's
    freeze propagates as the same stated refusal those doors give."""
    from . import corrections
    try:
        return corrections.apply(spec_id, cand_id,
                                 list(body.get("indices") or []))
    except (KeyError, PermissionError) as e:
        raise _err(e)
    except (ValueError, generate.GenerationError) as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/correction-intake/dismiss")
def api_correction_dismiss(spec_id: str, cand_id: str) -> dict:
    from . import corrections
    try:
        return corrections.dismiss(spec_id, cand_id)
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/feedback-retire")
def api_retire_feedback(spec_id: str, cand_id: str, body: dict) -> dict:
    """A rejection reason that was satisfied or superseded stops carrying
    into future prompts (user 2026-08-08: a stale "closer adherence"
    correction stood as a counter-order against the newer "remove the
    person"). The rejection and its history are untouched."""
    try:
        return generate.retire_feedback(spec_id, cand_id,
                                        bool(body.get("retired", True)))
    except KeyError as e:
        raise _err(e)


@app.delete("/api/specs/{spec_id}/candidates/{cand_id}")
def api_delete_candidate(spec_id: str, cand_id: str) -> dict:
    try:
        return generate.delete_candidate(spec_id, cand_id)
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/lighting-study")
async def api_lighting_study(spec_id: str, cand_id: str, body: dict) -> dict:
    try:
        return generate.create_lighting_study(
            spec_id, cand_id, body.get("atmospheres"))
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/derive/palette")
def api_derive_palette(spec_id: str) -> dict:
    try:
        return generate.derive_palette(spec_id)
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/derive/materials")
async def api_derive_materials(spec_id: str, body: dict) -> dict:
    try:
        return await run_in_threadpool(
            generate.derive_materials, spec_id,
            body.get("provider") or generate.preferred_provider(),
            body.get("image_size", "2K"))
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"materials derivation failed: {e}")


@app.post("/api/references/crop")
async def api_crop_reference(body: dict) -> dict:
    """Harvest a cell: crop a region of an approved candidate or reference
    image into a new reference with its own narrow role."""
    from PIL import Image
    import io

    src = body.get("source") or {}
    rect = body.get("rect") or {}
    role = str(body.get("role", "")).strip()
    if not role:
        raise HTTPException(422, "role is required")
    try:
        x, y, w, h = (max(0.0, min(1.0, float(rect.get(k, 0)))) for k in ("x", "y", "w", "h"))
    except (TypeError, ValueError):
        raise HTTPException(422, "rect must be relative {x,y,w,h} in 0..1")
    if w < 0.02 or h < 0.02:
        raise HTTPException(422, "crop region is too small")

    try:
        if src.get("type") == "candidate":
            p = generate.candidate_image_path(str(src.get("spec_id", "")), str(src.get("id", "")))
            origin = f"{src.get('id')} of {src.get('spec_id')}"
        elif src.get("type") == "reference":
            p = store.reference_image_path(str(src.get("id", "")))
            origin = str(src.get("id"))
        else:
            raise HTTPException(422, "source.type must be candidate or reference")
    except KeyError as e:
        # Traversal-shaped ids are a 404, not a 500 (same contract as
        # api_candidate_image).
        raise _err(e)
    if p is None:
        raise HTTPException(404, "source image not found")

    with Image.open(p) as im:
        im = im.convert("RGB")
        box = (round(x * im.width), round(y * im.height),
               round(min(1.0, x + w) * im.width), round(min(1.0, y + h) * im.height))
        crop = im.crop(box)
        buf = io.BytesIO()
        crop.save(buf, "PNG")

    ref = store.add_reference(
        f"crop of {origin}.png", buf.getvalue(), role, [], [],
        notes=str(body.get("notes", "")) or f"cropped from {origin}")
    return store.set_reference_status(ref["id"], "APPROVED")


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/repair")
async def api_repair_region(request: Request, spec_id: str, cand_id: str,
                            mask: UploadFile = File(...),
                            instruction: str = Form(...),
                            ref_ids: str = Form("[]"),
                            provider: str = "openai") -> dict:
    try:
        ids = json.loads(ref_ids)
        if not isinstance(ids, list):
            raise ValueError
    except ValueError:
        raise HTTPException(422, "ref_ids must be a JSON list")
    # Flight recorder: the repair prompt belongs in the log (the middleware
    # only sees the multipart byte count).
    request.state.activity = {"instruction": instruction, "ref_ids": ids}
    try:
        mask_bytes = await mask.read()
        return await run_in_threadpool(
            generate.repair_region, spec_id, cand_id, mask_bytes, instruction,
            ids, provider)
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"region repair failed: {e}")


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/rerender")
async def api_rerender(spec_id: str, cand_id: str, body: dict) -> dict:
    """Re-performance for resolution: the take anchors itself, rendered at
    the requested size. Never interpolation — the no-upscaling rule stands."""
    try:
        return await run_in_threadpool(
            generate.rerender_full, spec_id, cand_id,
            body.get("image_size", "4K"), body.get("provider", "openai"))
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"re-render failed: {e}")


@app.post("/api/subjects/{sid}/link")
async def api_link_subject_ref(sid: str, body: dict) -> dict:
    """Link an EXISTING reference to a subject card, so library anchors and
    card mosaics stay one view of the same canon."""
    ref_id = str(body.get("ref_id", "")).strip()
    if store.get_reference(ref_id) is None:
        raise HTTPException(404, f"unknown reference: {ref_id}")
    try:
        return store.link_subject_ref(sid, ref_id)
    except KeyError as e:
        raise _err(e)


@app.post("/api/specs/{spec_id}/candidates/purge-rejected")
def api_purge_rejected(spec_id: str) -> dict:
    try:
        return generate.purge_rejected(spec_id)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))


@app.get("/api/specs/{spec_id}/candidates/{cand_id}/image")
def api_candidate_image(spec_id: str, cand_id: str, size: str = "full", thumb: bool = False):
    try:
        p = generate.candidate_variant_path(spec_id, cand_id, "thumb" if thumb else size)
        if p is None:
            # Base-keyed URLs (one board per unit): the take may live in a
            # sibling revision's directory — candidate ids are production-
            # global, so the first hit is the only hit.
            from . import revisions
            for rid in revisions.revisions_of(revisions.base_of(spec_id)):
                if rid == spec_id:
                    continue
                p = generate.candidate_variant_path(rid, cand_id,
                                                    "thumb" if thumb else size)
                if p is not None:
                    break
    except KeyError as e:  # traversal-shaped ids → the same 404 as unknown ids
        raise _err(e)
    if p is None:
        raise HTTPException(404, f"no image for {cand_id}")
    return FileResponse(p)


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/status")
async def api_candidate_status(spec_id: str, cand_id: str, body: dict) -> dict:
    try:
        return generate.set_candidate_status(
            spec_id, cand_id, body.get("status", ""), body.get("reason", ""))
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/unapprove")
async def api_candidate_unapprove(spec_id: str, cand_id: str) -> dict:
    """Withdraw an approval without rejecting the take (user 2026-08-16).
    Its own act because a rejection is a judgement that carries into every
    future prompt for the panel — wanting to edit the brief is not that."""
    try:
        return generate.unapprove_candidate(spec_id, cand_id)
    except KeyError as e:
        raise _err(e)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/candidates/{cand_id}/promote")
async def api_candidate_promote(spec_id: str, cand_id: str, body: dict) -> dict:
    """Promote an APPROVED render into the reference library with a role —
    this is how approved output becomes a canon anchor for future generations."""
    record = generate.get_candidate(spec_id, cand_id)
    if record is None:
        raise HTTPException(404, f"unknown candidate: {cand_id}")
    if record.get("status") != "APPROVED":
        raise HTTPException(422, f"{cand_id} is {record.get('status')}; only APPROVED "
                                 "renders can be promoted to references")
    p = generate.candidate_image_path(spec_id, cand_id)
    if p is None:
        raise HTTPException(404, f"image file missing for {cand_id}")
    role = str(body.get("role", "")).strip()
    if not role:
        raise HTTPException(422, "role is required")
    split = lambda v: [x.strip() for x in str(v or "").split(",") if x.strip()]
    ref = store.add_reference(
        f"{cand_id} ({spec_id}).png", p.read_bytes(), role,
        split(body.get("controls")), split(body.get("does_not_control")),
        body.get("notes", f"promoted from {cand_id} of {spec_id}"))
    ref = store.set_reference_status(ref["id"], "APPROVED")
    generate.mark_promoted(spec_id, cand_id, ref["id"])
    return ref


# --------------------------------------------------------------- style bible

@app.get("/api/style-bible")
def api_get_style_bible() -> dict:
    return {"text": generate.load_style_bible(),
            "is_default": not paths.BIBLE.exists(),
            "rev": int(store.load_app_state().get("bible_rev", 0))}


@app.put("/api/style-bible")
async def api_save_style_bible(body: dict) -> dict:
    text = str(body.get("text", "")).strip()
    if not text:
        raise HTTPException(422, "style bible cannot be empty")
    generate.save_style_bible(text + "\n")
    state = store.load_app_state()
    state["bible_rev"] = int(state.get("bible_rev", 0)) + 1
    store.save_app_state(state)
    return {"text": text + "\n", "is_default": False, "rev": state["bible_rev"]}


@app.get("/api/bible/sections")
def api_bible_sections() -> dict:
    return bible.sections_catalog()


# ----------------------------------------------------------------- subjects

@app.get("/api/subjects")
def api_list_subjects() -> list[dict]:
    return store.list_subjects()


@app.post("/api/subjects")
async def api_add_subject(body: dict) -> dict:
    try:
        return store.add_subject(
            str(body.get("name", "")), str(body.get("kind", "CHARACTER")),
            str(body.get("subtitle", "")), body.get("traits") or [],
            str(body.get("source", "")))
    except (ValueError, FileExistsError) as e:
        raise _err(e)


@app.put("/api/subjects/{sid}")
async def api_update_subject(sid: str, body: dict) -> dict:
    try:
        return store.update_subject(sid, body)
    except KeyError as e:
        raise _err(e)


@app.delete("/api/subjects/{sid}")
def api_delete_subject(sid: str) -> dict:
    try:
        return store.delete_subject(sid)
    except KeyError as e:
        raise _err(e)


@app.post("/api/subjects/{sid}/reference")
async def api_subject_reference(sid: str, file: UploadFile = File(...)) -> dict:
    """Upload a reference image INTO a subject's title card: the reference is
    created with the card's role (e.g. CHARACTER_LIKENESS — JOHN STANNER),
    approved, and linked to the card."""
    subj = store.get_subject(sid)
    if subj is None:
        raise HTTPException(404, f"unknown subject: {sid}")
    role = f"{store.SUBJECT_ROLE_PREFIX[subj['kind']]} — {subj['name'].upper()}"
    try:
        ref = store.add_reference(
            file.filename or "subject.png", await file.read(), role, [], [],
            notes=f"reference for subject {subj['name']} ({sid})")
    except ValueError as e:
        raise _err(e)
    store.set_reference_status(ref["id"], "APPROVED")
    return store.link_subject_ref(sid, ref["id"])


# ------------------------------------------------------------ setup wizard

@app.get("/api/wizard/samples")
def api_list_samples() -> list[dict]:
    return generate.list_samples()


@app.get("/api/wizard/samples/{provider}/image")
def api_sample_image(provider: str):
    p = generate.sample_image_path(provider)
    if p is None:
        raise HTTPException(404, f"no sample for {provider}")
    return FileResponse(p)


@app.post("/api/wizard/samples/{provider}")
async def api_generate_sample(provider: str, body: dict = Body(default={})) -> dict:
    try:
        return await run_in_threadpool(
            generate.sample_probe, provider, body.get("subject"))
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"sample generation failed: {e}")


@app.get("/api/wizard/analysis")
def api_get_wizard_analysis() -> dict:
    return store.load_wizard_analysis() or {}


@app.put("/api/wizard/analysis")
def api_put_wizard_analysis(body: dict) -> dict:
    store.save_wizard_analysis(body)
    return {"ok": True}


@app.post("/api/wizard/analyze")
async def api_wizard_analyze(body: dict) -> dict:
    provider = body.get("provider", "gemini")
    try:
        analysis = await run_in_threadpool(wizard.analyze_screenplay, provider)
    except autofill.AutofillError as e:
        raise HTTPException(422, str(e))
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"screenplay analysis failed: {e}")
    # Re-run merge: confirmed languages/environments and answered questions
    # survive; the fresh read's new finds arrive PROPOSED (Gap 5 rulings).
    analysis = wizard.merge_analysis(store.load_wizard_analysis() or {}, analysis)
    # Faction self-check — one extra cheap pass. Its failure degrades
    # silently to the main result; the read itself is already valid.
    try:
        proposed = await run_in_threadpool(
            wizard.faction_self_check, analysis, provider)
        have = {str(w.get("name", "")).casefold()
                for w in analysis.get("design_worlds", [])}
        analysis.setdefault("design_worlds", []).extend(
            m for m in proposed if m["name"].casefold() not in have)
    except Exception:
        pass
    analysis["analyzed_at"] = store.utcnow()
    analysis["screenplay"] = (store.load_app_state().get("screenplay") or {}).get("file", "")
    store.save_wizard_analysis(analysis)
    return analysis


# One question per anchor, plus the three no anchor can hold (user ruling
# 2026-08-16 — "we now have duplicative entries"). `texture` and `light`
# are new: the interview and the style anchors were the same four
# questions asked in two media, and folding the words INTO the anchor
# cards left World Texture and Cinematography without a words half.
# `palette` predates the split and holds legacy "palette and light" text
# from before it — it lands on the Color Palette card, which is where the
# larger half of it always belonged.
_INTERVIEW_FIELDS = ("texture", "palette", "light", "medium", "never",
                     "notes")


def _fold_touchstones() -> None:
    """`touchstones` is retired (user ruling 2026-08-16). It was the one
    input with no fence — "Blade Runner 2049" sets texture, palette, light
    and medium at once, by the weakest of the three routes to a render, so
    it could not reliably deliver the look but could reliably muddy the
    four answers given deliberately. What a production already typed is
    not thrown away: it folds into the standing notes, where an unfenced
    sentence is at least labelled as one."""
    p = _interview_path()
    if not p.exists():
        return
    try:
        saved = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if "touchstones" not in saved:
        return
    old = str(saved.pop("touchstones", "")).strip()
    if old:
        note = f"Visual touchstones (from the retired interview): {old}"
        saved["notes"] = chr(10).join(
            x for x in (str(saved.get("notes", "")).strip(), note) if x)
    store._atomic_write_json(p, saved)


def _fold_touchstones_everywhere() -> None:
    """Every production, once, at boot — a migration runs, it is not
    offered (ruled 2026-08-16)."""
    with paths.SWITCH_LOCK:
        prev = paths.ACTIVE_PROJECT
        try:
            for proj in paths.list_projects():
                paths.set_project(proj["slug"])
                try:
                    _fold_touchstones()
                except Exception:  # noqa: BLE001 — boot must survive
                    pass
        finally:
            paths.set_project(prev)


def _interview_path():
    return paths.DATA / "interview.json"


@app.get("/api/wizard/interview")
def api_get_interview() -> dict:
    """The look interview, persisted per production (user ruling
    2026-08-01: a refresh must never lose it). Lives in data/ so backups
    carry it."""
    p = _interview_path()
    if not p.exists():
        return {k: "" for k in _INTERVIEW_FIELDS}
    try:
        saved = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {k: "" for k in _INTERVIEW_FIELDS}
    return {k: str(saved.get(k, "")) for k in _INTERVIEW_FIELDS}


@app.put("/api/wizard/interview")
async def api_save_interview(body: dict) -> dict:
    fields = {k: str(body.get(k, "")).strip() for k in _INTERVIEW_FIELDS}
    paths.ensure_dirs()
    store._atomic_write_json(_interview_path(), fields)
    return fields


@app.post("/api/wizard/draft-bible")
async def api_wizard_draft_bible(body: dict) -> dict:
    answers = body.get("answers", {})
    # The saved interview backstops the payload — a draft from any client
    # state still honors what the director recorded.
    saved = api_get_interview()
    for k in _INTERVIEW_FIELDS:
        if not str(answers.get(k, "")).strip() and saved.get(k):
            answers[k] = saved[k]
    try:
        return await run_in_threadpool(
            wizard.draft_bible, answers, body.get("provider", "gemini"))
    except autofill.AutofillError as e:
        raise HTTPException(422, str(e))
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"bible draft failed: {e}")


@app.get("/api/lessons")
def api_get_lessons() -> list[dict]:
    return generate.load_lessons()


@app.post("/api/lessons")
async def api_add_lesson(body: dict) -> dict:
    reason = str(body.get("reason", "")).strip()
    if not reason:
        raise HTTPException(422, "reason is required")
    generate.add_lesson(reason, source="manual")
    return {"ok": True}


@app.post("/api/lessons/remove")
async def api_remove_lesson(body: dict) -> dict:
    if not generate.remove_lesson(str(body.get("reason", ""))):
        raise HTTPException(404, "no such lesson")
    return {"ok": True}


# ------------------------------------------------------------------ autofill

@app.post("/api/specs/autofill")
async def api_autofill_spec(body: dict) -> dict:
    _require_production_design()
    try:
        return await run_in_threadpool(
            autofill.autofill_spec,
            str(body.get("specification_id", "")).strip(),
            str(body.get("prompt", "")),
            body.get("mode", "CANON_EXTRACTION"),
            body.get("provider", "gemini"),
            str(body.get("board_type", "")))
    except autofill.AutofillError as e:
        raise HTTPException(422, str(e))
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"auto-fill failed: {e}")


# ------------------------------------------------------------------ assembly

@app.get("/api/specs/{spec_id}/slot-map")
def api_slot_map(spec_id: str, width: int = 3840, height: int = 2160,
                 variant: str = "default") -> dict:
    """Slot geometry + per-slot readiness verdicts before any render is
    spent — makes the never-upscaled rule visible in advance. `variant`
    previews a presentation layout: default | grid | hero:<panel>."""
    try:
        return assemble.slot_map(spec_id, width, height, variant)
    except KeyError as e:
        raise _err(e)
    except assemble.AssemblyError as e:
        raise HTTPException(422, str(e))


@app.post("/api/specs/{spec_id}/assemble")
async def api_assemble(spec_id: str, body: dict) -> dict:
    try:
        return await run_in_threadpool(
            assemble.assemble_board, spec_id,
            int(body.get("width", 3840)), int(body.get("height", 2160)),
            body.get("variant", "default"))
    except KeyError as e:
        raise _err(e)
    except assemble.AssemblyError as e:
        raise HTTPException(422, str(e))


@app.get("/api/specs/{spec_id}/boards")
def api_list_boards(spec_id: str) -> list[dict]:
    """The UNIT's assembled boards — aggregated across every revision's
    directory (new boards land in the base dir; legacy per-revision
    boards still list), ordered by board id."""
    from . import revisions
    import json as _json
    out = []
    for rid in revisions.revisions_of(revisions.base_of(spec_id)) or [spec_id]:
        d = paths.BOARDS_DIR / paths.safe_id(rid)
        if not d.exists():
            continue
        out += [_json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(d.glob("BOARD-*.json"))]
    return sorted(out, key=lambda b: str(b.get("candidate_id", "")))


# ------------------------------------------------- sheets & lookbooks (§9)
# The sheet grammar: one mechanism for boards and lookbook pages
# (SHEET_SYSTEM_PLAN). SheetError → 422, KeyError → 404 throughout.

def _sheet_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except sheet.SheetError as e:
        raise HTTPException(422, str(e))
    except KeyError as e:
        raise _err(e)


@app.post("/api/specs/{spec_id}/arrange")
def api_arrange(spec_id: str) -> dict:
    """Stage 05's one new door: idempotent — a spec has at most one BOARD
    sheet, created on first call from the spec's current slot map."""
    if store.get_spec(spec_id) is None:
        raise HTTPException(404, spec_id)
    try:
        return sheet.arrange_board(spec_id)
    except sheet.SheetError as e:
        raise HTTPException(422, str(e))
    except assemble.AssemblyError as e:
        raise HTTPException(422, str(e))


# The sheet API was trimmed to the arrange room's needs 2026-08-12 (the
# Lookbook authoring surface was rolled back, user): sheets are made only
# by /api/specs/{id}/arrange, and the composer verbs that remain are
# slot edits (fill/crop/frac), readiness, render and export. The model
# layer keeps its full grammar — it is the boards' renderer.

# /candidates and /looks are declared BEFORE /{sheet_id} — FastAPI
# matches in declaration order, and neither must be captured as an id.
@app.get("/api/sheets/candidates")
def api_fill_candidates() -> list[dict]:
    return sheet.fill_candidates()


@app.get("/api/sheets/looks")
def api_looks_catalog() -> list[dict]:
    return looks.catalog()


@app.get("/api/sheets/{sheet_id}")
def api_get_sheet(sheet_id: str) -> dict:
    rec = _sheet_call(sheet.get_sheet, sheet_id)
    if rec is None:
        raise HTTPException(404, sheet_id)
    # BOARD sheets predating the arrange-room physics get an arrangement
    # inferred from their slot geometry (not persisted by a read).
    if rec.get("archetype") == "BOARD" and "arrangement" not in rec:
        rec["arrangement"] = sheet.derive_arrangement(rec)
    # The sheet states where its panels actually live (derived, never
    # persisted): blocks render inside the content rect — margins plus
    # the masthead band — not the full page. The arrange room MUST work
    # at this field's aspect or it previews panel shapes the export will
    # not have (user bug, 2026-08-13: room disagreed with map + export).
    cw, ch, cx, cy = sheet._content_rect_fracs(rec)
    rec["content_rect"] = {"w": cw, "h": ch, "x": cx, "y": cy}
    return rec


@app.put("/api/sheets/{sheet_id}/arrangement")
def api_set_arrangement(sheet_id: str, body: dict) -> dict:
    """The arrange room's commit door (2026-08-12): the client edits a
    rows/columns/cells structure; the server maps it to slot geometry and
    stores both. Gesture math in the client is feedback only."""
    return _sheet_call(sheet.set_arrangement, sheet_id, body)


@app.put("/api/sheets/{sheet_id}/blocks/{block_id}/slots/{slot_id}")
def api_set_slot(sheet_id: str, block_id: str, slot_id: str,
                 body: dict) -> dict:
    return _sheet_call(sheet.set_slot, sheet_id, block_id, slot_id, body)


@app.put("/api/sheets/{sheet_id}/look")
def api_set_look(sheet_id: str, body: dict) -> dict:
    """Persist (or clear, key null) a board's presentation look. The look
    is a sibling of the arrangement — it survives every arrange commit."""
    return _sheet_call(looks.set_look, sheet_id, body.get("key"),
                       body.get("options"))


@app.get("/api/sheets/{sheet_id}/readiness")
def api_sheet_readiness(sheet_id: str) -> dict:
    def _ready():
        rec = sheet.get_sheet(sheet_id)
        if rec is None:
            raise KeyError(sheet_id)
        # Judge what will ship: a look shrinks the panel area, and the
        # gate must be readable before export is hit.
        return sheet.readiness(looks.dressed(rec))
    return _sheet_call(_ready)


@app.post("/api/sheets/{sheet_id}/render")
async def api_render_sheet(sheet_id: str, body: dict) -> Response:
    """Preview PNG at a scale — the same renderer as export, so the two
    cannot drift (§10)."""
    rec = sheet.get_sheet(sheet_id)
    if rec is None:
        raise HTTPException(404, sheet_id)
    scale = max(0.05, min(1.0, float(body.get("scale", 0.25))))
    # Look resolution: by default the stored look dresses the render; a
    # "look" key in the body overrides WITHOUT persisting (the picker's
    # preview cards). {"look": null} previews the naked INK sheet.
    if "look" in body:
        rec = dict(rec)
        rec.pop("look", None)
        ov = body.get("look")
        if ov and ov.get("key"):
            try:
                rec["look"] = {"key": str(ov["key"]),
                               "options": looks.resolved_options(
                                   str(ov["key"]), ov.get("options"))}
            except KeyError:
                raise HTTPException(422, f"unknown look: {ov.get('key')}")
            except sheet.SheetError as e:
                raise HTTPException(422, str(e))
    try:
        view = looks.dressed(rec)
    except sheet.SheetError as e:
        raise HTTPException(422, str(e))
    # Preview-scale renders feed slot images from the md display tier —
    # a picker card must not decode a dozen 4K PNGs. Full-scale renders
    # (and export/assemble, which never pass a tier) read the source.
    tier = "md" if scale <= 0.25 else "full"
    import io

    manifest: list = []

    def _render() -> bytes:
        img = sheet_render.render_sheet(view, scale, allow_letterbox=True,
                                        manifest=manifest,
                                        image_tier=tier)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        return buf.getvalue()
    try:
        data = await run_in_threadpool(_render)
    except sheet.SheetError as e:
        raise HTTPException(422, str(e))
    # R2 (canon pass): geometry is computed once and declared — the
    # renderer's own rects ride the response; the overlay aims with them
    # and measures nothing.
    return Response(content=data, media_type="image/png",
                    headers={"X-Sheet-Rev": str(rec.get("rev", 0)),
                             "X-Sheet-Scale": str(scale),
                             "X-Sheet-Geometry": json.dumps(manifest),
                             "Cache-Control": "no-store"})


@app.post("/api/sheets/{sheet_id}/export")
async def api_export_sheet(sheet_id: str, body: dict) -> dict:
    try:
        out = await run_in_threadpool(
            sheet_render.export_sheet, sheet_id,
            str(body.get("format", "png")))
    except sheet.SheetError as e:
        raise HTTPException(422, str(e))
    except KeyError as e:
        raise _err(e)
    return {"ok": True, "file": out.name}


@app.get("/api/sheets/{sheet_id}/export/{name}")
def api_download_sheet_export(sheet_id: str, name: str) -> FileResponse:
    p = sheet.sheet_export_dir(sheet_id) / paths.safe_id(name)
    if not p.exists():
        raise HTTPException(404, name)
    return FileResponse(p, filename=p.name)


# /api/lookbooks* removed 2026-08-12: the Lookbook surface was rolled back
# (user). The fill tray moved to /api/sheets/candidates (declared above the
# /{sheet_id} routes); any lookbook JSON files on disk stay inert.


# ------------------------------------------------------------------------ ui

# The stale-origin fix (user-hit twice, 2026-08-04). Two layers:
# 1. Direct browser hits on the internal *.up.railway.app host redirect
#    permanently to the branded address when one exists — customers
#    consolidate on ONE origin. Proxied traffic (X-Forwarded-Host set by
#    our router) and /api/* (healthz probes, programmatic use) pass.
# 2. "/" serves index.html with version-stamped asset URLs, so a cached
#    document can never pin last month's app.js — the URL itself changes
#    each release.
PUBLIC_URL = os.environ.get("SCREENBOARD_PUBLIC_URL", "").rstrip("/")


@app.middleware("http")
async def canonical_host(request: Request, call_next):
    # The EFFECTIVE external host decides: Railway's edge fronts direct
    # hits and forwards the railway hostname; our wildcard router
    # forwards the BRANDED hostname. Presence of the header proves
    # nothing (production-caught 2026-08-04) — its value does.
    #
    # ERR_TOO_MANY_REDIRECTS, production 2026-08-04: when the branded
    # address resolves straight to this service (a per-tenant custom
    # domain still attached at Railway, bypassing the router), the app
    # still sees a railway host and redirects to the branded address —
    # which lands here again. Three guards make a loop impossible:
    #   1. our router marks its traffic with a header Railway cannot set;
    #   2. one redirect only — the marker on the way out is refused on
    #      the way in;
    #   3. 302, never 301 — a misconfiguration must not be cached into
    #      the customer's browser permanently.
    host = (request.headers.get("x-forwarded-host")
            or request.headers.get("host", "")).split(":", 1)[0].lower()
    if (PUBLIC_URL and host.endswith(".up.railway.app")
            and request.method in ("GET", "HEAD")
            and not request.url.path.startswith("/api/")
            and request.headers.get("x-screenboard-router") != "1"
            and "_sb" not in request.query_params):
        q = request.url.query
        return RedirectResponse(
            PUBLIC_URL + request.url.path + ("?" + q + "&_sb=1" if q else "?_sb=1"),
            status_code=302)
    return await call_next(request)


def _stamped_index() -> HTMLResponse:
    html = (paths.STATIC / "index.html").read_text(encoding="utf-8")
    ver = paths.ROOT / "VERSION"
    v = ver.read_text(encoding="utf-8").strip() if ver.exists() else "dev"
    html = html.replace('src="/app.js"', f'src="/app.js?v={v}"')
    html = html.replace('href="/styles.css"', f'href="/styles.css?v={v}"')
    # The tab remembers what it booted with, so a long-lived SPA tab can
    # notice the studio moving on beneath it (stale-tab bar, 2026-08-05).
    html = html.replace(
        "</head>", f'<script>window.SB_BOOT_VERSION={v!r};</script></head>')
    # Freshness is the no-cache middleware's job (tested contract, all
    # three UI paths) — do not set a second, weaker rule here.
    return HTMLResponse(html)


@app.get("/")
def serve_index() -> HTMLResponse:
    return _stamped_index()


app.mount("/", StaticFiles(directory=str(paths.STATIC), html=True), name="static")


@app.exception_handler(404)
async def not_found(request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": getattr(exc, "detail", "not found")}, status_code=404)
    # Deep links (user 2026-08-12): /panels/SPEC-0001, /boards/…/arrange —
    # any non-API path boots the SPA, which routes the address. Serve the
    # SAME stamped document as "/": the bare file would pin unversioned
    # asset URLs and reopen the stale-tab hole on shared links.
    return _stamped_index()
