from __future__ import annotations

import json

from fastapi import Body, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import activity, assemble, autofill, bible, generate, paths, store, wizard
from .validation import check_spec, full_validate

app = FastAPI(title="Screenboard Studio", version="0.2.0")
paths.ensure_dirs()


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

    t0 = _time.perf_counter()
    try:
        response = await call_next(req)
    except Exception as e:
        activity.log({"method": request.method, "path": request.url.path,
                      "body": body_summary, "status": 500, "error": str(e)[:500],
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
                  "body": body_summary, "status": response.status_code,
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

    return {
        "project": "The Beltminers",
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
        "suggested_roles": store.SUGGESTED_ROLES,
    }


# ----------------------------------------------------------------- screenplay

@app.post("/api/screenplay")
async def api_upload_screenplay(file: UploadFile = File(...)) -> dict:
    content = await file.read()
    if not content:
        raise HTTPException(422, "empty file")
    return store.set_screenplay(file.filename or "screenplay.pdf", content)


# ----------------------------------------------------------------- references

@app.get("/api/references")
def api_list_references() -> list[dict]:
    return store.list_references()


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
                              body.get("mode", "CANON_EXTRACTION"))
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
    oenv = os.environ.get("OPENAI_API_KEY", "").strip()
    return {"openai_env_key_hint": f"…{oenv[-4:]}" if oenv else None,
            "gemini_api_key_set": bool(gkey),
            "gemini_api_key_hint": f"…{gkey[-4:]}" if gkey else None,
            "openai_api_key_set": bool(okey),
            "openai_api_key_hint": f"…{okey[-4:]}" if okey else None,
            "model": generate.MODEL,
            "openai_model": generate.OPENAI_MODEL,
            "providers": {k: v["label"] for k, v in generate.PROVIDERS.items()},
            "default_provider": generate.DEFAULT_PROVIDER,
            "preferred_provider": generate.preferred_provider()}


@app.post("/api/settings")
async def api_save_settings(body: dict) -> dict:
    s = generate.load_settings()
    if "gemini_api_key" in body:
        s["gemini_api_key"] = str(body["gemini_api_key"]).strip()
    if "openai_api_key" in body:
        s["openai_api_key"] = str(body["openai_api_key"]).strip()
    if "preferred_provider" in body:
        p = str(body["preferred_provider"]).strip()
        if p not in generate.PROVIDERS:
            raise HTTPException(422, f"unknown provider: {p}")
        s["preferred_provider"] = p
    generate.save_settings(s)
    return api_get_settings()


@app.post("/api/settings/test")
async def api_test_settings(body: dict = None) -> dict:
    provider = (body or {}).get("provider", generate.DEFAULT_PROVIDER)
    try:
        return await run_in_threadpool(generate.test_connection, provider)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"{provider} connection failed: {e}")


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
async def api_repair_region(spec_id: str, cand_id: str,
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


@app.post("/api/specs/{spec_id}/candidates/purge-rejected")
def api_purge_rejected(spec_id: str) -> dict:
    try:
        return generate.purge_rejected(spec_id)
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))


@app.get("/api/specs/{spec_id}/candidates/{cand_id}/image")
def api_candidate_image(spec_id: str, cand_id: str):
    p = generate.candidate_image_path(spec_id, cand_id)
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
    return ref


# --------------------------------------------------------------- style bible

@app.get("/api/style-bible")
def api_get_style_bible() -> dict:
    return {"text": generate.load_style_bible(),
            "is_default": not paths.BIBLE.exists()}


@app.put("/api/style-bible")
async def api_save_style_bible(body: dict) -> dict:
    text = str(body.get("text", "")).strip()
    if not text:
        raise HTTPException(422, "style bible cannot be empty")
    generate.save_style_bible(text + "\n")
    return {"text": text + "\n", "is_default": False}


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
    try:
        analysis = await run_in_threadpool(
            wizard.analyze_screenplay, body.get("provider", "gemini"))
    except autofill.AutofillError as e:
        raise HTTPException(422, str(e))
    except generate.GenerationError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(502, f"screenplay analysis failed: {e}")
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

@app.post("/api/specs/{spec_id}/assemble")
async def api_assemble(spec_id: str, body: dict) -> dict:
    try:
        return await run_in_threadpool(
            assemble.assemble_board, spec_id,
            int(body.get("width", 3840)), int(body.get("height", 2160)))
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
