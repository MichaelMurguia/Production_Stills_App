from __future__ import annotations

import hmac
import json
import os

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import (FileResponse, HTMLResponse, JSONResponse,
                               RedirectResponse, Response)
from fastapi.staticfiles import StaticFiles

from . import (activity, assemble, autofill, backup, bible, generate,
               insights, paths, store, wizard)
from .validation import check_spec, full_validate

app = FastAPI(title="Screenboard Studio", version="0.2.0")
paths.ensure_dirs()

# ---------------------------------------------------- cloud workspace gate
# Set SCREENBOARD_ACCESS_TOKEN and the whole app sits behind a login that
# accepts exactly that token (hosted tenants get theirs at purchase).
# Unset — every standalone install — none of this exists and the app stays
# fully offline-capable.
ACCESS_TOKEN = os.environ.get("SCREENBOARD_ACCESS_TOKEN", "")
_AUTH_EXEMPT = {"/login", "/api/login", "/api/healthz", "/styles.css", "/favicon.ico"}

_LOGIN_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Screenboard Studio — workspace login</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/styles.css"></head>
<body style="display:flex;align-items:center;justify-content:center;min-height:100vh">
<div class="panel" id="gate" style="width:min(460px,92vw)">
  <h2>Screenboard access</h2>
  <p class="hint">This is a private Screenboard Studio. Paste the access
  token from your order confirmation to enter.</p>
  <form id="f" class="row" style="margin-top:12px">
    <input type="password" id="tok" placeholder="access token" style="flex:1" autofocus>
    <button class="primary">Enter</button>
  </form>
  <p class="mini hidden" id="err" style="color:var(--bad);margin-top:8px">That token doesn't match this Screenboard.</p>
</div>
<div class="panel hidden" id="signing" style="width:min(460px,92vw)">
  <h2>Signing you in&hellip;</h2>
</div>
<script>
// Arriving with a store handoff (/login#token): never flash the token
// form — show the quiet signing-in state instead.
if (location.hash.length > 1) {
  document.getElementById("gate").classList.add("hidden");
  document.getElementById("signing").classList.remove("hidden");
}
const attempt = async token => {
  const r = await fetch("/api/login", { method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }) });
  if (r.ok) { location.replace("/"); return; }
  document.getElementById("signing").classList.add("hidden");
  document.getElementById("gate").classList.remove("hidden");
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
  history.replaceState(null, "", "/login");
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
    return resp


@app.middleware("http")
async def workspace_auth(request: Request, call_next):
    if not ACCESS_TOKEN or request.url.path in _AUTH_EXEMPT:
        return await call_next(request)
    if hmac.compare_digest(request.cookies.get("sb_session", ""), ACCESS_TOKEN):
        return await call_next(request)
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "workspace login required"}, status_code=401)
    return RedirectResponse("/login", status_code=303)


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
    resp.set_cookie("sb_session", ACCESS_TOKEN, max_age=30 * 24 * 3600,
                    httponly=True, samesite="lax",
                    secure=request.url.scheme == "https")
    return resp


@app.get("/api/healthz")
def api_healthz():
    """Liveness + serving revision — the provisioner's readiness probe."""
    return {"ok": True, "rev": os.environ.get("RAILWAY_GIT_COMMIT_SHA", "local")[:12]}


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
    return {"active": paths.ACTIVE_PROJECT, "projects": projects}


@app.get("/api/projects/backup")
def api_backup_project(slug: str = "") -> Response:
    """One zip of one project — screenplay, bible, references, sheets,
    boards, approvals. API keys are never included."""
    try:
        payload, filename = backup.make_backup(slug)
    except KeyError as e:
        raise _err(e)
    return Response(payload, media_type="application/zip",
                    headers={"Content-Disposition":
                             f'attachment; filename="{filename}"'})


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
    paths.set_project(slug)
    paths.save_active_project(slug)
    paths.ensure_dirs()
    insights._text_cache.clear()  # screenplay cache is per-project


@app.post("/api/projects")
def api_create_project(body: dict) -> dict:
    name = str(body.get("name", "")).strip()
    if not name:
        raise HTTPException(422, "give the project a name")
    slug = "".join(c if c.isalnum() or c in "._-" else "-" for c in name).strip("-_.").lower()
    if not slug:
        raise HTTPException(422, "the name needs at least one letter or digit")
    if (paths.PROJECTS_DIR / slug).exists():
        raise HTTPException(409, f"project already exists: {slug}")
    d = paths.PROJECTS_DIR / slug
    d.mkdir(parents=True)
    (d / "project.json").write_text(
        json.dumps({"name": name, "created_at": store.utcnow()}, indent=2) + "\n",
        encoding="utf-8")
    _switch_project(slug)
    return {"active": paths.ACTIVE_PROJECT, "projects": paths.list_projects()}


@app.post("/api/projects/activate")
def api_activate_project(body: dict) -> dict:
    slug = str(body.get("slug", ""))
    if slug and not (paths.PROJECTS_DIR / slug).is_dir():
        raise HTTPException(404, f"unknown project: {slug}")
    _switch_project(slug)
    return {"active": paths.ACTIVE_PROJECT, "projects": paths.list_projects()}


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
                body_summary = json.loads(raw)
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
        # The active screenboard's name — never a hardcoded project.
        "project": paths._project_name(
            paths._project_base(paths.ACTIVE_PROJECT), "Untitled Screenboard"),
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
def api_reference_image(ref_id: str, thumb: bool = False):
    p = store.reference_image_path(ref_id, thumb=thumb)
    if p is None:
        raise HTTPException(404, f"no image for {ref_id}")
    return FileResponse(p)


# ---------------------------------------------------------------------- specs

@app.get("/api/specs")
def api_list_specs() -> list[dict]:
    return store.list_specs()


@app.post("/api/specs")
async def api_new_spec(body: dict) -> dict:
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
def api_revise_spec(spec_id: str) -> dict:
    try:
        return store.revise_spec(spec_id)
    except (KeyError, FileExistsError) as e:
        raise _err(e)


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
    customs = []
    for e in generate.custom_engines():
        pid = f"custom:{e['id']}"
        engines[pid] = {"configured": True, "source": "settings",
                        "last_test": tests.get(pid)}
        customs.append({"id": e["id"], "label": e.get("label") or e["id"],
                        "model": e["model"], "base_url": e.get("base_url", ""),
                        "key_hint": f"…{e['api_key'][-4:]}"})
    return {"openai_env_key_hint": f"…{oenv[-4:]}" if oenv else None,
            "gemini_api_key_set": bool(gkey),
            "gemini_api_key_hint": f"…{gkey[-4:]}" if gkey else None,
            "openai_api_key_set": bool(okey),
            "openai_api_key_hint": f"…{okey[-4:]}" if okey else None,
            "model": generate.MODEL,
            "openai_model": generate.OPENAI_MODEL,
            "providers": {k: v["label"] for k, v in generate.all_providers().items()},
            "aspects": generate.aspect_catalog(),
            "board_templates": store.BOARD_TEMPLATES,
            "custom_engines": customs,
            "default_provider": generate.DEFAULT_PROVIDER,
            "preferred_provider": generate.preferred_provider(),
            "engines": engines}


@app.post("/api/settings")
async def api_save_settings(body: dict) -> dict:
    s = generate.load_settings()
    if "gemini_api_key" in body:
        s["gemini_api_key"] = str(body["gemini_api_key"]).strip()
    if "openai_api_key" in body:
        s["openai_api_key"] = str(body["openai_api_key"]).strip()
    if "preferred_provider" in body:
        p = str(body["preferred_provider"]).strip()
        if p not in generate.all_providers():
            raise HTTPException(422, f"unknown provider: {p}")
        s["preferred_provider"] = p
    generate.save_settings(s)
    return api_get_settings()


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


@app.get("/api/specs/{spec_id}/candidates")
def api_list_candidates(spec_id: str) -> list[dict]:
    return generate.list_candidates(spec_id)


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

    if src.get("type") == "candidate":
        p = generate.candidate_image_path(str(src.get("spec_id", "")), str(src.get("id", "")))
        origin = f"{src.get('id')} of {src.get('spec_id')}"
    elif src.get("type") == "reference":
        p = store.reference_image_path(str(src.get("id", "")))
        origin = str(src.get("id"))
    else:
        raise HTTPException(422, "source.type must be candidate or reference")
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
def api_candidate_image(spec_id: str, cand_id: str):
    try:
        p = generate.candidate_image_path(spec_id, cand_id)
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


@app.post("/api/wizard/draft-bible")
async def api_wizard_draft_bible(body: dict) -> dict:
    try:
        return await run_in_threadpool(
            wizard.draft_bible, body.get("answers", {}), body.get("provider", "gemini"))
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
    try:
        return await run_in_threadpool(
            autofill.autofill_spec,
            str(body.get("specification_id", "")).strip(),
            str(body.get("prompt", "")),
            body.get("mode", "CANON_EXTRACTION"),
            body.get("provider", "gemini"))
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
    d = paths.BOARDS_DIR / spec_id
    if not d.exists():
        return []
    import json as _json
    return [_json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(d.glob("BOARD-*.json"))]


# ------------------------------------------------------------------------ ui

app.mount("/", StaticFiles(directory=str(paths.STATIC), html=True), name="static")


@app.exception_handler(404)
async def not_found(request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": getattr(exc, "detail", "not found")}, status_code=404)
    return FileResponse(paths.STATIC / "index.html")
