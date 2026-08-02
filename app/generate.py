from __future__ import annotations

import json
import re
from pathlib import Path

from . import bible, mockflow, paths, store

MODEL = "gemini-3-pro-image"  # default provider's model (Gemini / Nano Banana Pro)
OPENAI_MODEL = "gpt-image-2"
OPENAI_CHAT_MODEL = "gpt-5.6"  # mainline model that rewrites the prompt, as ChatGPT does
OPENAI_CHAT_IMAGE_MODEL = "chatgpt-image-latest"  # whatever image model ChatGPT itself uses

PROVIDERS = {
    "gemini": {"model": MODEL, "label": "Gemini (Nano Banana Pro)"},
    "openai": {"model": OPENAI_MODEL, "label": "OpenAI (GPT Image 2, direct)"},
    "openai-chat": {"model": f"{OPENAI_CHAT_IMAGE_MODEL} via {OPENAI_CHAT_MODEL}",
                    "label": "OpenAI (ChatGPT pipeline)"},
}
DEFAULT_PROVIDER = "gemini"


def custom_engines() -> list[dict]:
    """User-added image engines (Settings → Engines & keys). The contract:
    the endpoint must speak the OpenAI Images API (images.generate /
    images.edit) at its base_url with the given key and model. Stored in
    data/settings.json under custom_engines."""
    out = []
    for e in load_settings().get("custom_engines", []):
        if e.get("id") and e.get("api_key") and e.get("model"):
            out.append(e)
    return out


def debug_tools_enabled() -> bool:
    """Debug tools exist only where the OWNER runs the app: the env flag
    is set on the user's own machines and, for cloud studios, by the
    provisioner only on workspaces whose purchase email is in the store's
    OWNER_EMAILS. Customers never see the tab, the endpoints, or the
    mock provider (user ruling 2026-08-03: linked to my account)."""
    import os
    return bool(os.environ.get("SCREENBOARD_DEBUG_TOOLS"))


def mock_enabled() -> bool:
    """Debug tools → Mock engine: the whole pipeline at zero cost."""
    return debug_tools_enabled() and bool(load_settings().get("debug_mock"))


def all_providers() -> dict:
    """Built-in engines plus every user-added one (ids 'custom:<id>'),
    plus every ENABLED connector model (ids 'or:<id>' / 'fal:<id>'),
    plus the mock engine while the debug toggle is on."""
    providers = dict(PROVIDERS)
    for e in custom_engines():
        providers[f"custom:{e['id']}"] = {
            "model": e["model"], "label": e.get("label") or e["id"],
            "custom": True}
    try:
        from . import connectors as cx
        for m in cx.enabled_records():
            providers[m["id"]] = {
                "model": m["provider_model_id"], "label": m["label"],
                "connector": m["connector"], "refs": m.get("refs"),
                "max_px": m.get("max_px"), "price": m.get("price_per_image"),
                "aspect_enum": m.get("aspect_enum"), "task": m.get("task"),
                "status": m.get("status")}
    except Exception:
        pass  # a corrupt connectors file must never hide the built-ins
    if mock_enabled():
        providers[mockflow.PROVIDER_ID] = {
            "model": mockflow.MODEL_NAME, "label": mockflow.LABEL,
            "mock": True}
    return providers


def _custom_engine(provider: str) -> dict:
    eng = next((e for e in custom_engines()
                if f"custom:{e['id']}" == provider), None)
    if eng is None:
        raise GenerationError(f"unknown custom engine: {provider}")
    return eng

DEFAULT_BOARD_TYPE = "LOCATION"  # legacy specs predate types; they behaved as location boards

IMAGE_SIZES = {"1K", "2K", "4K"}

# Aspect catalog — the single source of truth for every ratio the app
# offers. `id` is the exact string stored on candidate records; film
# formats carry their names into the dropdowns. Per-engine support follows
# each API's real contract: Gemini accepts a fixed enum; the OpenAI Images
# API takes arbitrary pixel dimensions (so GPT Image 2 and custom engines
# render everything); the ChatGPT pipeline's image tool has exactly three
# presets — it never silently approximates anymore.
ASPECT_CATALOG = [
    {"id": "2.55:1", "label": "CinemaScope (1953) — 2.55:1"},
    {"id": "2.39:1", "label": "Scope — 2.39:1"},
    {"id": "21:9",   "label": "21:9 — ultrawide"},
    {"id": "16:9",   "label": "16:9 — HD"},
    {"id": "3:2",    "label": "VistaVision — 3:2"},
    {"id": "1.37:1", "label": "Academy — 1.37:1"},
    {"id": "4:3",    "label": "4:3"},
    {"id": "1:1",    "label": "1:1 — square"},
    {"id": "3:4",    "label": "3:4"},
    {"id": "2:3",    "label": "2:3"},
    {"id": "9:16",   "label": "9:16 — tall"},
]
ASPECT_RATIOS = {a["id"] for a in ASPECT_CATALOG}
GEMINI_RATIOS = {"21:9", "16:9", "3:2", "4:3", "5:4", "1:1", "4:5", "3:4",
                 "2:3", "9:16"}  # the API's fixed enum
CHAT_RATIOS = {"1:1", "3:2", "2:3"}  # the image tool's three true presets

MAX_REFERENCE_IMAGES = 14


def aspect_value(aspect_ratio: str) -> float:
    w, h = (float(x) for x in aspect_ratio.split(":"))
    return w / h


def aspect_catalog() -> list[dict]:
    """Catalog rows with decimal value and the provider ids that can
    genuinely render each ratio — the UI greys the rest."""
    providers = all_providers()
    out = []
    for a in ASPECT_CATALOG:
        engines = []
        for pid in providers:
            if pid == "gemini":
                ok = a["id"] in GEMINI_RATIOS
            elif pid == "openai-chat":
                ok = a["id"] in CHAT_RATIOS
            elif pid.startswith(("or:", "fal:")):
                # A connector model with a stated aspect enum keeps it;
                # one without is treated as arbitrary, judged at render.
                enum = providers[pid].get("aspect_enum")
                ok = a["id"] in enum if enum else True
            else:  # openai + custom engines: arbitrary pixel sizes
                ok = True
            if ok:
                engines.append(pid)
        out.append({**a, "value": round(aspect_value(a["id"]), 4),
                    "engines": engines})
    return out

CANDIDATE_STATUSES = {"CANDIDATE", "APPROVED", "REJECTED"}


class GenerationError(Exception):
    pass

# Content-policy refusals are a stated condition, not a raw error blob
# (user ruling 2026-08-02, after a legitimate scene — an overdose tableau
# from the screenplay — was refused). The app never routes around a
# provider's safety system; it explains the refusal and the craft answer.
_SAFETY_MARKS = ("safety system", "content policy", "content_policy",
                 "safety_violations", "blocked by", "responsible ai",
                 "prohibited_content", "moderation")


def _wrap_engine_error(engine: str, e: Exception) -> "GenerationError":
    msg = str(e)
    if any(m in msg.lower() for m in _SAFETY_MARKS):
        return GenerationError(
            f"ENGINE REFUSED — CONTENT POLICY: {engine} declined to render "
            f"this panel's content. This is the provider's safety system, "
            f"not an app error, and it cannot be bypassed. The craft answer "
            f"is usually to restage the panel — imply the sensitive element "
            f"rather than inventory it — or try a different engine, whose "
            f"policy line may differ. Provider said: {msg[:300]}")
    return GenerationError(f"{engine} generation failed: {e}")



# --------------------------------------------------------------- style bible

def load_style_bible() -> str:
    """The Art Direction Bible is the single source of truth; the legacy
    data/style_bible.md condensation is a per-project fallback. There is
    deliberately NO template default (director's ruling 2026-08-01):
    every production's rendering style is set by its own Cinematography
    and Rendering content — an empty return is a stated upstream gap,
    never silently painted over with another film's art direction."""
    text = bible.load_text()
    if text:
        return text
    p = paths.DATA / "style_bible.md"
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def save_style_bible(text: str) -> None:
    bible.save_text(text)


# ---------------------------------------------------------- rejection lessons

def _lessons_path():
    return paths.DATA / "rejection_lessons.json"


def load_lessons() -> list[dict]:
    p = _lessons_path()
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def add_lesson(reason: str, source: str) -> None:
    reason = reason.strip()
    if not reason:
        return
    lessons = load_lessons()
    if any(l["reason"].casefold() == reason.casefold() for l in lessons):
        return
    lessons.append({"reason": reason, "source": source, "added_at": store.utcnow()})
    paths.ensure_dirs()
    store._atomic_write_json(_lessons_path(), lessons)


def remove_lesson(reason: str) -> bool:
    lessons = load_lessons()
    kept = [l for l in lessons if l["reason"].casefold() != reason.strip().casefold()]
    if len(kept) == len(lessons):
        return False
    store._atomic_write_json(_lessons_path(), kept)
    return True


def project_negatives() -> list[str]:
    """Project-wide negative constraints: recorded prohibited inventions plus
    every lesson learned from rejected candidates."""
    out: list[str] = []
    if paths.PROJECT_STATE.exists():
        state = json.loads(paths.PROJECT_STATE.read_text(encoding="utf-8"))
        out.extend(str(x) for x in state.get("prohibited_inventions", []))
    out.extend(l["reason"] for l in load_lessons())
    seen: set[str] = set()
    return [x for x in out if not (x.casefold() in seen or seen.add(x.casefold()))]


# ------------------------------------------------------------------ settings

def load_settings() -> dict:
    """Settings (API keys, engines, preferences) are INSTALL-level — they
    follow the user across projects. Pre-multi-project installs kept them
    in data/settings.json; that copy is read until the first save moves
    them to the install home."""
    if paths.SETTINGS.exists():
        try:
            return json.loads(paths.SETTINGS.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            # A corrupt file must not brick every route — set it aside
            # (nothing is destroyed) and present a fresh, stated blank.
            paths.SETTINGS.replace(paths.SETTINGS.with_suffix(".json.corrupt"))
            return {}
    legacy = paths.HOME / "data" / "settings.json"  # pre-multi-project home
    if legacy.exists():
        return json.loads(legacy.read_text(encoding="utf-8"))
    return {}


def save_settings(settings: dict) -> None:
    # Atomic — a truncated settings.json would 500 every route, including
    # the Settings page the user would need to repair it.
    paths.ensure_dirs()
    store._atomic_write_json(paths.SETTINGS, settings)


def _client(timeout_ms: int = 300_000):
    import os
    from google import genai
    key = (load_settings().get("gemini_api_key", "").strip()
           or os.environ.get("GEMINI_API_KEY", "").strip()
           or os.environ.get("GOOGLE_API_KEY", "").strip())
    if not key:
        raise GenerationError(
            "No Gemini API key configured. Add it under Settings on the Dashboard.")
    return genai.Client(api_key=key, http_options={"timeout": timeout_ms})


def _openai_client(timeout_s: float = 300.0):
    import os
    from openai import OpenAI
    key = (load_settings().get("openai_api_key", "").strip()
           or os.environ.get("OPENAI_API_KEY", "").strip())
    if not key:
        raise GenerationError(
            "No OpenAI API key configured. Add it under Settings on the Dashboard.")
    return OpenAI(api_key=key, timeout=timeout_s)


def test_connection(provider: str = DEFAULT_PROVIDER) -> dict:
    if provider not in all_providers():
        raise GenerationError(f"unknown provider: {provider}")
    if provider.startswith("custom:"):
        from openai import OpenAI
        eng = _custom_engine(provider)
        client = OpenAI(api_key=eng["api_key"], base_url=eng["base_url"],
                        timeout=20.0)
        try:
            model = client.models.retrieve(eng["model"])
            got = getattr(model, "id", eng["model"])
        except Exception:
            # Not every OpenAI-compatible server implements /models —
            # reaching it and being authorized is the meaningful part.
            client.models.list()
            got = eng["model"]
        return {"ok": True, "provider": provider, "model": got}
    if provider.startswith(("or:", "fal:")):
        from . import connectors as cx
        rec = next((m for m in cx.enabled_records() if m["id"] == provider), None)
        if rec is None:
            raise GenerationError(f"unknown provider: {provider}")
        pub = cx.sync(rec["connector"])
        if pub["status"] != "SYNCED":
            raise GenerationError(
                f"{pub['label']}: {pub['status']} — "
                f"{pub['last_error'].get('detail', 'see Settings')}")
        return {"ok": True, "provider": provider, "model": rec["provider_model_id"]}
    if provider in ("openai", "openai-chat"):
        client = _openai_client(timeout_s=20.0)
        want = OPENAI_MODEL if provider == "openai" else OPENAI_CHAT_MODEL
        model = client.models.retrieve(want)
        return {"ok": True, "provider": provider, "model": getattr(model, "id", want)}
    client = _client(timeout_ms=20_000)
    model = client.models.get(model=MODEL)
    return {"ok": True, "provider": "gemini", "model": getattr(model, "name", MODEL)}


# ------------------------------------------------------------ prompt compile

def _feedback_archive_path() -> Path:
    return paths.DATA / "feedback_archive.json"


def archive_feedback(spec_id: str, panel_id: str, reason: str, source: str) -> None:
    """Preserve a rejection directive when its candidate record is deleted —
    institutional memory must outlive the image file."""
    reason = (reason or "").strip()
    if not reason:
        return
    p = _feedback_archive_path()
    items = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    base = re.sub(r"_R\d+$", "", spec_id)
    if any(i["base"] == base and i["panel_id"] == panel_id
           and i["reason"].casefold() == reason.casefold() for i in items):
        return
    items.append({"base": base, "panel_id": panel_id, "reason": reason,
                  "source": source, "archived_at": store.utcnow()})
    paths.ensure_dirs()
    store._atomic_write_json(p, items)


def rejection_feedback(spec_id: str, panel_id: str) -> list[str]:
    """Directives from the user's rejections of this panel's earlier candidates,
    across all revisions of the same spec — from live candidate records plus the
    archive of deleted ones. These are corrections to FOLLOW — injected in their
    own prompt section, never under a never-include header."""
    base = re.sub(r"_R\d+$", "", spec_id)
    out: list[str] = []
    seen: set[str] = set()

    def add(reason: str) -> None:
        reason = (reason or "").strip()
        if reason and reason.casefold() not in seen:
            seen.add(reason.casefold())
            out.append(reason)

    p = _feedback_archive_path()
    if p.exists():
        for i in json.loads(p.read_text(encoding="utf-8")):
            if i.get("base") == base and i.get("panel_id") == panel_id:
                add(i.get("reason", ""))
    if paths.BOARDS_DIR.exists():
        for d in sorted(paths.BOARDS_DIR.iterdir()):
            if not d.is_dir() or re.sub(r"_R\d+$", "", d.name) != base:
                continue
            for meta in sorted(d.glob("CAND-*.json")):
                r = json.loads(meta.read_text(encoding="utf-8"))
                if r.get("status") == "REJECTED" and r.get("panel_id") == panel_id:
                    add(str(r.get("status_reason", "")))
    return out


def _style_context(spec: dict, panel: dict) -> str:
    """Bible sections that apply to this panel; falls back to the flat style
    bible text if the bible file is missing."""
    haystack = " ".join(str(x) for x in [
        spec.get("subject", ""), spec.get("render_intent", ""),
        panel.get("title", ""), panel.get("purpose", ""),
        " ".join(panel.get("required_objects", [])),
        " ".join(panel.get("forbidden_objects", [])),
    ])
    # Explicit per-spec selection is the governed path; absent fields fall
    # back to keyword inference inside render_context. A panel's own scope
    # (design_languages / environment) overrides the sheet's for that panel
    # only. Environments never infer — no scope means none carried.
    if panel.get("design_languages"):
        languages = panel["design_languages"]
    elif "design_languages" in spec:
        languages = spec["design_languages"]
    else:
        languages = None
    language = bible.render_context(
        haystack,
        languages,
        spec.get("scene_lessons") if "scene_lessons" in spec else None,
        environments=([panel["environment"]] if panel.get("environment")
                      else spec.get("environments") or []),
    ) or load_style_bible().strip()
    if not language:
        # Backstop behind the breakdown gate: never render without the
        # production's own art direction, never substitute a template's.
        raise GenerationError(
            "no rendering language — save the Art Direction Bible "
            "(Production Design) before rendering")
    return language


def _setting_lines(spec: dict, panel: dict) -> list[str]:
    """The SETTING block — slugline discipline. Scene boards carry one time of
    day for every panel; location and lighting-study boards take it per panel.
    Asset and master boards get neutral presentation instead of a slugline."""
    btype = str(spec.get("board_type") or DEFAULT_BOARD_TYPE).upper()
    if btype in ("ASSET", "MASTER"):
        return ["SETTING",
                "Asset presentation — neutral, even presentation of the subject. "
                "No dramatic scene lighting, no implied narrative moment, unless "
                "the panel purpose explicitly asks for one.",
                ""]
    s = spec.get("setting") or {}
    int_ext = str(s.get("int_ext", "")).strip()
    location = str(s.get("location", "")).strip()
    if btype in ("LOCATION", "LIGHTING_STUDY"):
        tod = str(panel.get("time_of_day", "")).strip() or str(s.get("time_of_day", "")).strip()
    else:
        tod = str(s.get("time_of_day", "")).strip()
    if not (int_ext or location or tod):
        return []
    place = f"{int_ext}. {location}".strip(". ").strip() if (int_ext or location) else ""
    slug = " — ".join(x for x in [place, tod.upper() if tod else ""] if x)
    lines = ["SETTING", slug,
             "This setting governs light direction, color temperature, shadow, and "
             "atmosphere for this panel. It OVERRIDES the hour, hue, or weather of "
             "any attached style image."]
    atmo = str(s.get("atmosphere", "")).strip()
    if atmo:
        lines.insert(2, f"Atmosphere: {atmo}")
    return lines + [""]


def compile_panel_prompt(spec: dict, panel: dict, refs: list[dict]) -> str:
    """Mechanical translation of one approved panel into render instructions.
    Mirrors scripts/compile_prompt.py but scoped to a single panel, with
    reference-role boundaries spelled out. Adds nothing creative."""
    from common import stable_hash  # scripts/ on sys.path via app.paths

    lines = [
        f"{store.project_name().upper()} PRODUCTION RENDER — SINGLE PANEL",
        f"SPECIFICATION: {spec['specification_id']} (hash {stable_hash(spec)[:16]})",
        f"PANEL: {panel['id']} — {panel.get('title', panel.get('purpose', ''))}",
        f"MODE: {spec['mode']}",
        "",
        "NON-NEGOTIABLE SOURCE RULES",
        "Render only what this panel specification requires. Do not invent additional "
        "worldbuilding, objects, culture, technology, fauna, vehicles, symbols, "
        "characters, props, or action. Omit unspecified content rather than filling space.",
        "",
    ]
    lines += _setting_lines(spec, panel)
    if str(spec.get("scene", "")).strip():
        lines += ["THE SCENE",
                  str(spec["scene"]).strip(),
                  ""]
    lines += [
        "PANEL PURPOSE",
        panel.get("purpose", ""),
        "",
        "DETAIL BUDGET",
        ("Hero panel: full rendering attention on the primary subject; "
         "secondary surfaces and ground cover simplify. Readable forms first — "
         "texture only where it states material, scale, wear, or manufacture."
         if panel.get("composition_role") == "hero" else
         "Supporting panel: medium detail. Simplify secondary surfaces and "
         "ground cover into large value shapes; never let texture become the "
         "subject."),
        "",
        _style_context(spec, panel),
        "",
        "BOARD-SPECIFIC TREATMENT",
        str(spec.get("render_intent", "Painterly production concept art with visible "
            "brushwork; production-development treatment, not glossy marketing art.")),
        "This is one panel of a production board, not a complete board: render a "
        "single full-bleed image. Do not render any text, labels, captions, titles, "
        "borders, panel frames, or watermarks.",
        "",
        "REQUIRED CONTENT",
    ]
    lines += ([f"- {x}" for x in panel.get("required_objects", [])]
              or ["- No specific objects required: compose this panel from its "
                  "PANEL PURPOSE, using only content the canon rules above support."])

    # Canon subject identities: when a required object is a cast/subject card,
    # its screenplay-derived identity goes into the prompt by name — the
    # model's prior on a NAMED thing is stronger than any attached photo.
    idents = []
    seen_subj = set()
    subjects = store.list_subjects()  # one read, not one per object
    for obj in panel.get("required_objects", []):
        o = str(obj).casefold()
        for s in subjects:
            n = s["name"].casefold()
            if s["id"] not in seen_subj and (n in o or o in n) and (s.get("traits") or s.get("subtitle")):
                seen_subj.add(s["id"])
                idents.append(f"- {s['name']} ({s['kind']}): "
                              + " ".join([s.get("subtitle", "")] + s.get("traits", [])).strip())
    if idents:
        lines += ["", "SUBJECT IDENTITIES — required content above includes these canon "
                  "subjects. Render each as EXACTLY what it is named to be — never a "
                  "generic substitute of its type:"]
        lines += idents
    lines += ["", "FORBIDDEN CONTENT"]
    forbidden = list(panel.get("forbidden_objects", [])) + list(spec.get("forbidden_elements", []))
    seen: set[str] = set()
    forbidden = [x for x in forbidden if not (x.casefold() in seen or seen.add(x.casefold()))]
    lines += [f"- {x}" for x in forbidden] or ["- None recorded"]
    feedback = rejection_feedback(str(spec.get("specification_id", "")), panel.get("id", ""))
    feedback_keys = {f.casefold() for f in feedback}
    negatives = [n for n in project_negatives() if n.casefold() not in feedback_keys]
    if negatives:
        lines += ["", "PROJECT LESSONS LEARNED — standing corrections from previously "
                  "rejected work. Each item is a rule: if it names unwanted content, "
                  "exclude that content; if it states a directive, follow it:"]
        lines += [f"- {x}" for x in negatives]
    if feedback:
        lines += ["", "REJECTION FEEDBACK — the director's corrections from rejecting "
                  "earlier candidates of this exact panel. These are instructions to "
                  "FOLLOW, not content to avoid. Each one overrides any conflicting "
                  "default above:"]
        lines += [f"- {x}" for x in feedback]

    if refs:
        lines += ["", "APPROVED REFERENCE ROLES",
                  "Each attached reference image controls ONLY its assigned scope. "
                  "Match its subject closely within that scope; it controls nothing else."]
        lines += _reference_role_lines(refs)

    lines += ["", f"SCALE: {panel.get('scale', 'unspecified')}",
              f"COMPOSITION ROLE: {panel.get('composition_role', 'distinct production question')}",
              "",
              "FINAL INSTRUCTION",
              "The output is a CANDIDATE — UNAPPROVED. Do not add unsupported decorative content."]
    return "\n".join(lines)


def _reference_role_lines(refs: list[dict]) -> list[str]:
    """Per-attachment scope declarations — what each reference image controls
    and what it must not. Shared by panel prompts and the bake-off samples."""
    style_defaults = {
        "BOARD_RENDERING_STYLE": (
            "the rendering and painting style of the artwork only — medium, "
            "brushwork, finish, surface texture",
            "content, subjects, composition, or layout"),
        "CINEMATOGRAPHY_STYLE": (
            "the film's photographic CHARACTER only — contrast handling, "
            "tonal depth, naturalism, lens and framing feel",
            "this panel's time of day, hue, or weather. The image is one "
            "moment from the film, not this panel's lighting: take the "
            "panel's actual light and palette from THE SCENE, the panel "
            "purpose, and the Lighting Language, not from this image's "
            "specific hour or color"),
        "LOCATION_GEOMETRY": (
            "the location's geometry, structure, layout, and composition — "
            "match them closely; this is the SAME place and camera setup",
            "lighting, palette, atmosphere, time of day, or weather — those "
            "are set by SETTING and vary per study panel"),
        "VEHICLE_GEOMETRY": (
            "this EXACT vehicle's body geometry — proportions, panel shapes, "
            "intakes, lights, wheels, details. It is this specific vehicle, "
            "not a generic vehicle of its type; where the panel shows an angle "
            "an attached image covers, match that image closely",
            "the vehicle's placement, viewing angle, lighting, or the scene"),
        "CHARACTER_LIKENESS": (
            "this character's facial likeness, build, hair, and age — the "
            "same recognizable person in every render",
            "costume, pose, expression context, lighting, or the scene"),
        "PROP_REFERENCE": (
            "this exact object's design, construction, and materials",
            "its placement, scale in frame, lighting, or the scene"),
    }
    lines: list[str] = []
    for i, r in enumerate(refs, 1):
        head = store.role_head(r.get("role", ""))
        d_controls, d_not = style_defaults.get(head, ("its assigned role", ""))
        controls = ", ".join(r.get("controls", [])) or d_controls
        lines.append(f"- Attached image {i} ({r['id']}, role {r['role']}): "
                     f"controls {controls}.")
        not_ctrl = ", ".join(r.get("does_not_control", [])) or d_not
        if not_ctrl:
            lines.append(f"  It does NOT control: {not_ctrl}.")
    return lines


# ---------------------------------------------------------------- candidates

def _spec_board_dir(spec_id: str) -> Path:
    d = paths.BOARDS_DIR / paths.safe_id(spec_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _resolve_generation_inputs(spec_id: str, panel_id: str,
                               ref_ids: list[str]) -> tuple[dict, dict, list[dict]]:
    spec = store.get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)
    if not store.spec_locked(spec_id):
        raise GenerationError(
            f"{spec_id} is not approved. Only approved, locked specifications may generate.")
    panel = next((p for p in spec.get("panels", []) if p.get("id") == panel_id), None)
    if panel is None:
        raise KeyError(f"unknown panel: {panel_id}")

    refs = []
    for rid in ref_ids:
        r = store.get_reference(rid)
        if r is None:
            raise KeyError(f"unknown reference: {rid}")
        # Canon rule enforced in code: only APPROVED references may anchor
        # a generation. Provisional and rejected/quarantined refs are refused.
        if r["status"] != "APPROVED":
            raise GenerationError(
                f"{rid} is {r['status']}, not APPROVED — it cannot be attached to a generation.")
        refs.append(r)

    # Style anchors (board rendering style, cinematography style) are art
    # direction, not subject reference — they apply to every generation
    # automatically, ahead of the panel's subject references.
    seen_ids = {r["id"] for r in refs}
    refs = [r for r in store.auto_style_references() if r["id"] not in seen_ids] + refs

    # Lighting studies are anchored to their parent board's approved geometry:
    # same place, same camera — only the light varies.
    gid = str(spec.get("geometry_ref") or "")
    if gid and gid not in {r["id"] for r in refs}:
        g = store.get_reference(gid)
        if g is None or g["status"] != "APPROVED":
            raise GenerationError(
                f"geometry anchor {gid} is missing or not APPROVED — this lighting "
                "study cannot generate without its location anchor.")
        refs.insert(0, g)

    if len(refs) > MAX_REFERENCE_IMAGES:
        raise GenerationError(f"at most {MAX_REFERENCE_IMAGES} reference images per generation")
    return spec, panel, refs


def list_candidates(spec_id: str) -> list[dict]:
    d = paths.BOARDS_DIR / paths.safe_id(spec_id)
    if not d.exists():
        return []
    out = []
    for meta in sorted(d.glob("CAND-*.json")):
        out.append(json.loads(meta.read_text(encoding="utf-8")))
    return out


def get_candidate(spec_id: str, cand_id: str) -> dict | None:
    p = paths.BOARDS_DIR / paths.safe_id(spec_id) / f"{paths.safe_id(cand_id)}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def candidate_image_path(spec_id: str, cand_id: str) -> Path | None:
    p = paths.BOARDS_DIR / paths.safe_id(spec_id) / f"{paths.safe_id(cand_id)}.png"
    return p if p.exists() else None


def _render_ready(p: Path) -> Path:
    """Compose-time backstop for legacy library files: sniff the ACTUAL
    format and transcode anything the engines refuse (AVIF 400'd a live
    generation 2026-08-02) to a cached sibling JPEG. Intake normalizes
    going forward (store.RENDER_SAFE_FORMATS); this rescues files that
    predate it without re-uploading."""
    from PIL import Image
    try:
        with Image.open(p) as im:
            fmt = (im.format or "").upper()
    except Exception as e:
        raise GenerationError(f"unreadable reference image {p.name}: {e}")
    if fmt in store.RENDER_SAFE_FORMATS:
        return p
    safe = p.with_name(f"{p.stem}.render.jpg")
    if not safe.exists():
        with Image.open(p) as im:
            im.convert("RGB").save(safe, "JPEG", quality=95)
    return safe


def _reference_image_paths(refs: list[dict]) -> list[Path]:
    out = []
    for r in refs:
        p = store.reference_image_path(r["id"])
        if p is None:
            raise GenerationError(f"image file missing for {r['id']}")
        out.append(_render_ready(p))
    return out


def _render_gemini(prompt: str, ref_paths: list[Path],
                   image_size: str, aspect_ratio: str, out_path: Path) -> str:
    from google.genai import types
    from PIL import Image

    contents: list = [prompt]
    for p in ref_paths:
        im = Image.open(p)
        im.load()  # read fully and release the file handle (Windows locks)
        contents.append(im)

    client = _client()
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            ),
        ),
    )

    image_part = None
    note_text = []
    for part in (response.parts or []):
        if getattr(part, "text", None):
            note_text.append(part.text)
        elif part.as_image() is not None:
            image_part = part.as_image()
    if image_part is None:
        raise GenerationError(
            "Gemini returned no image. " + (" ".join(note_text)[:500] or "No details provided."))
    image_part.save(out_path)
    return " ".join(note_text)[:2000]


# OpenAI's Image API takes explicit pixel dimensions rather than Gemini's
# size-class + aspect-ratio pair, with hard constraints: edges must be
# multiples of 16, longest edge <= 3840, total pixels <= 8,294,400.
_OPENAI_AREA = {"1K": 1024 * 1024, "2K": 2048 * 2048, "4K": 3840 * 2160}


def openai_size(image_size: str, aspect_ratio: str) -> str:
    import math
    ar_w, ar_h = (float(x) for x in aspect_ratio.split(":"))  # 2.55:1 is legal
    area = _OPENAI_AREA[image_size]
    w = math.sqrt(area * ar_w / ar_h)
    if w > 3840:
        w = 3840
    h = w * ar_h / ar_w
    if h > 3840:
        h = 3840
        w = h * ar_w / ar_h
    w, h = (max(256, round(x / 16) * 16) for x in (w, h))
    return f"{w}x{h}"


def legal_openai_size(width: int, height: int) -> str:
    """Snap arbitrary pixel dimensions onto the Images API's legal grid
    (edges ×16, longest edge ≤3840, area ≤8,294,400) without changing the
    aspect — used so repairs can request their source's own resolution."""
    import math
    w, h = float(width), float(height)
    scale = min(3840 / max(w, h), math.sqrt(8_294_400 / (w * h)), 1.0)
    w, h = w * scale, h * scale
    return f"{max(256, round(w / 16) * 16)}x{max(256, round(h / 16) * 16)}"


def _render_openai(prompt: str, ref_paths: list[Path],
                   image_size: str, aspect_ratio: str, out_path: Path) -> str:
    import base64

    client = _openai_client()
    size = openai_size(image_size, aspect_ratio)
    try:
        if ref_paths:
            # NOTE: no input_fidelity — gpt-image-2 rejects it (it was a
            # gpt-image-1.x parameter; the API returns invalid_input_fidelity_model).
            files = [p.open("rb") for p in ref_paths]
            try:
                response = client.images.edit(
                    model=OPENAI_MODEL, image=files, prompt=prompt,
                    size=size, quality="high")
            finally:
                for f in files:
                    f.close()
        else:
            response = client.images.generate(
                model=OPENAI_MODEL, prompt=prompt, size=size, quality="high")
    except Exception as e:
        raise _wrap_engine_error("OpenAI", e) from e

    if not getattr(response, "data", None) or not response.data[0].b64_json:
        raise GenerationError("OpenAI returned no image.")
    out_path.write_bytes(base64.b64decode(response.data[0].b64_json))
    return getattr(response.data[0], "revised_prompt", "") or ""


def _render_custom(provider: str, prompt: str, ref_paths: list[Path],
                   image_size: str, aspect_ratio: str, out_path: Path) -> str:
    """User-added engine: OpenAI Images API contract at the engine's
    base_url. References attach via images.edit when present; servers that
    return URLs instead of base64 are handled. Provider errors surface
    verbatim — the app can't paper over a third party."""
    import base64
    from openai import OpenAI

    eng = _custom_engine(provider)
    client = OpenAI(api_key=eng["api_key"], base_url=eng["base_url"])
    size = openai_size(image_size, aspect_ratio)
    name = eng.get("label") or eng["id"]
    try:
        if ref_paths:
            files = [p.open("rb") for p in ref_paths]
            try:
                response = client.images.edit(
                    model=eng["model"], image=files if len(files) > 1 else files[0],
                    prompt=prompt, size=size)
            finally:
                for f in files:
                    f.close()
        else:
            response = client.images.generate(
                model=eng["model"], prompt=prompt, size=size)
    except Exception as e:
        raise _wrap_engine_error(name, e) from e

    data = getattr(response, "data", None)
    if data and getattr(data[0], "b64_json", None):
        out_path.write_bytes(base64.b64decode(data[0].b64_json))
    elif data and getattr(data[0], "url", None):
        # The URL comes from a user-configured engine — https only (no
        # file:// reads into a served artifact), bounded time and size.
        import urllib.request
        url = str(data[0].url)
        if not url.startswith(("https://", "http://")):
            raise GenerationError(
                f"{name} returned a non-HTTP image URL — refused.")
        with urllib.request.urlopen(url, timeout=120) as r:
            img = r.read(64 * 1024 * 1024 + 1)
        if len(img) > 64 * 1024 * 1024:
            raise GenerationError(f"{name} returned an image over 64 MB — refused.")
        out_path.write_bytes(img)
    else:
        raise GenerationError(f"{name} returned no image.")
    return getattr(data[0], "revised_prompt", "") or ""


# The rewriter gets one job: turn the spec into vivid render prose. The spec's
# canon constraints must survive the rewrite verbatim in effect, so the
# instruction pins invention to zero — same rule the spec itself states.
_REWRITER_RULES = """\
You are the render-prompt compiler for a locked film-production art board.
Rewrite the specification below into the strongest possible natural-language
prompt for the image generation tool, the way a director of photography would
describe the finished painting: one flowing description of subject, composition,
light, and paint handling.

Hard rules for your rewrite:
- Every item under REQUIRED CONTENT must appear, described concretely.
- Nothing under FORBIDDEN CONTENT or PROJECT LESSONS LEARNED may appear, and do
  not invent ANY object, character, creature, symbol, text, or worldbuilding
  the specification does not list. Sparse and specific beats full and generic.
- The VISUAL STYLE section is non-negotiable art direction — bake it into the
  description rather than quoting it.
- Respect the reference-image roles exactly as scoped.
"""

def _rewriter_rules() -> str:
    """Base rewrite rules plus the bible's Drift Prevention Rule, so the
    rewriter acts as the Art Direction Guardian. Read live: bible edits
    propagate without a restart."""
    rules = _REWRITER_RULES
    drift = bible.drift_prevention()
    if drift:
        rules += ("\nBefore finalizing, act as the Art Direction Guardian and "
                  "answer this locked Drift Prevention Rule from the "
                  "specification and attached references alone:\n" + drift +
                  "\nAutomation note: where the rule says generation stops, you "
                  "instead OMIT the uncertain detail entirely — never guess.\n")
    return rules


def _rewriter_instructions() -> str:
    return _rewriter_rules() + """\
Then call the image generation tool exactly once with that prompt.

SPECIFICATION FOLLOWS
=====================
"""


def _draft_instructions() -> str:
    return _rewriter_rules() + """\
Output ONLY the finished render prompt text — no headings, no preamble, no
commentary, no markdown fences.

SPECIFICATION FOLLOWS
=====================
"""

_VERBATIM_INSTRUCTIONS = """\
Call the image generation tool exactly once. Use the following render prompt
verbatim — do not rewrite, expand, trim, or comment on it.

RENDER PROMPT FOLLOWS
=====================
"""


def _chat_model() -> str:
    return load_settings().get("openai_chat_model", "").strip() or OPENAI_CHAT_MODEL


def preferred_provider() -> str:
    p = load_settings().get("preferred_provider", "")
    if p in all_providers():
        return p
    # Ruled default (CONNECTORS_UI_PLAN C1): the ChatGPT image pipeline is
    # the recommended starting engine once an OpenAI key exists; without
    # one the recommendation is a stated gate, and Gemini leads if that
    # key is present instead. Never a preselected broken option.
    import os
    if load_settings().get("openai_api_key", "").strip() or \
            os.environ.get("OPENAI_API_KEY", "").strip():
        return "openai-chat"
    return DEFAULT_PROVIDER


def draft_render_prose(spec_id: str, panel_id: str, ref_ids: list[str]) -> dict:
    """ChatGPT-style prompt crafting as a first-class, reviewable artifact:
    rewrite the compiled spec into render prose WITHOUT generating an image,
    so the user can edit the exact text before committing a render to it."""
    spec, panel, refs = _resolve_generation_inputs(spec_id, panel_id, ref_ids)
    compiled = compile_panel_prompt(spec, panel, refs)
    client = _openai_client(timeout_s=120.0)
    chat_model = _chat_model()
    try:
        response = client.responses.create(
            model=chat_model, input=_draft_instructions() + compiled)
    except Exception as e:
        raise GenerationError(f"prose draft failed: {e}") from e
    text = (getattr(response, "output_text", "") or "").strip()
    if not text:
        raise GenerationError("prose draft failed: the model returned no text.")
    return {"prose": text, "chat_model": chat_model}


def _chat_tool_size(aspect_ratio: str) -> str:
    """The Responses API image_generation tool accepts ONLY 1024x1024,
    1024x1536, 1536x1024, or auto — arbitrary pixel sizes 400 with
    invalid_value. Pick by orientation; the pipeline therefore caps near
    1.5K regardless of the Size selection — use a direct engine for
    larger renders."""
    try:
        w, h = (int(x) for x in aspect_ratio.split(":"))
    except (ValueError, AttributeError):
        return "auto"
    if w > h:
        return "1536x1024"
    if h > w:
        return "1024x1536"
    return "1024x1024"


def _render_connector(provider: str, prompt: str, ref_paths: list[Path],
                      image_size: str, aspect_ratio: str, out_path: Path) -> str:
    """A render through an enabled connector model. Never a silent
    substitution: any failure raises and states itself — the take is not
    quietly sent to a different engine."""
    from . import connectors as cx
    rec = next((m for m in cx.enabled_records() if m["id"] == provider), None)
    if rec is None:
        raise GenerationError(f"unknown connector model: {provider}")
    key = cx.load_state().get(rec["connector"], {}).get("key", "")
    if not key:
        raise GenerationError(
            f"{rec['label']}: its connector is NOT CONNECTED — reconnect in "
            "Settings. The take was not rendered anywhere else.")
    try:
        if rec["connector"] == "openrouter":
            return cx.openrouter_generate(key, rec["provider_model_id"],
                                          prompt, ref_paths, out_path)
        return cx.fal_generate(key, rec, prompt, ref_paths,
                               image_size, aspect_ratio, out_path)
    except Exception as e:
        raise _wrap_engine_error(rec["label"], e) from e


def _render_openai_chat(prompt: str, ref_paths: list[Path],
                        image_size: str, aspect_ratio: str, out_path: Path,
                        verbatim: bool = False) -> str:
    import base64
    import mimetypes

    client = _openai_client()
    size = _chat_tool_size(aspect_ratio)
    chat_model = _chat_model()

    instructions = _VERBATIM_INSTRUCTIONS if verbatim else _rewriter_instructions()
    content: list[dict] = [{"type": "input_text", "text": instructions + prompt}]
    for p in ref_paths:
        mime = mimetypes.guess_type(p.name)[0] or "image/png"
        b64 = base64.b64encode(p.read_bytes()).decode()
        content.append({"type": "input_image", "image_url": f"data:{mime};base64,{b64}"})

    tool = {"type": "image_generation", "size": size, "quality": "high",
            "input_fidelity": "high", "model": OPENAI_CHAT_IMAGE_MODEL}
    try:
        try:
            response = client.responses.create(
                model=chat_model,
                input=[{"role": "user", "content": content}],
                tools=[tool],
                tool_choice={"type": "image_generation"},
            )
        except Exception as e:
            # Newer image models reject input_fidelity; retry once without it.
            if "input_fidelity" not in str(e):
                raise
            tool.pop("input_fidelity", None)
            response = client.responses.create(
                model=chat_model,
                input=[{"role": "user", "content": content}],
                tools=[tool],
                tool_choice={"type": "image_generation"},
            )
    except Exception as e:
        raise _wrap_engine_error("OpenAI (ChatGPT pipeline)", e) from e

    calls = [o for o in response.output if getattr(o, "type", "") == "image_generation_call"]
    if not calls or not getattr(calls[0], "result", None):
        text = getattr(response, "output_text", "") or "No details provided."
        raise GenerationError(f"OpenAI (ChatGPT pipeline) returned no image. {text[:500]}")
    out_path.write_bytes(base64.b64decode(calls[0].result))

    # Surface the rewrite for diagnostics: this is the prompt the image model
    # actually rendered, the same thing ChatGPT shows as its crafted prompt.
    notes = []
    revised = getattr(calls[0], "revised_prompt", "") or ""
    if revised:
        notes.append(f"REWRITTEN RENDER PROMPT ({chat_model}):\n{revised}")
    text = (getattr(response, "output_text", "") or "").strip()
    if text:
        notes.append(f"MODEL COMMENTARY:\n{text}")
    return "\n\n".join(notes)[:4000]


# ------------------------------------------------------------- sample probes

SAMPLE_PROBE_SUBJECT = (
    "A small, weathered workshop interior at dusk: a workbench with well-used "
    "tools, warm lantern light, a single figure working with their back "
    "half-turned. Quiet, lived-in, maintained.")


def _samples_dir() -> Path:
    d = paths.DATA / "samples"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sample_probe(provider: str, subject: str | None = None) -> dict:
    """One identical brief per engine, so the default model is chosen by
    looking at renders, not by guessing. The brief is a location from the
    screenplay (picked in the wizard) rendered under the saved Art Direction
    Bible and the approved style anchors — the same conditions real panel
    generations run under. Without a location, a generic scene is used."""
    if provider not in all_providers():
        raise GenerationError(f"provider must be one of {sorted(all_providers())}")
    subject = (subject or "").strip()
    style_refs = store.auto_style_references()
    ref_paths = _reference_image_paths(style_refs)
    language = bible.render_context("") or load_style_bible().strip()
    if not language:
        raise GenerationError("no rendering language — save the Art "
                              "Direction Bible before running a style probe")
    parts = [
        "STYLE SAMPLE PROBE — engine selection test",
        "",
        "Render ONE image demonstrating how you interpret this project's locked "
        "art direction.",
        "",
        language,
        "",
        "SUBJECT",
        (f"A location from this screenplay: {subject}.\n"
         "Render this location as one production concept panel — the place "
         "itself as it would appear in the film, composed and lit per the art "
         "direction above. Show only content the art direction and the "
         "location's name support; invent nothing else.")
        if subject else SAMPLE_PROBE_SUBJECT,
    ]
    if style_refs:
        parts += ["", "APPROVED REFERENCE ROLES",
                  "Each attached reference image controls ONLY its assigned scope. "
                  "Match it closely within that scope; it controls nothing else."]
        parts += _reference_role_lines(style_refs)
    parts += ["", "Render a single full-bleed image. No text, labels, or borders."]
    prompt = "\n".join(parts)
    out = _samples_dir() / f"{provider}.png"
    if provider == "mock":
        notes = mockflow.render(prompt, ref_paths, "1K", "16:9", out)
    elif provider == "openai-chat":
        notes = _render_openai_chat(prompt, ref_paths, "1K", "16:9", out, verbatim=True)
    elif provider == "openai":
        notes = _render_openai(prompt, ref_paths, "1K", "16:9", out)
    else:
        notes = _render_gemini(prompt, ref_paths, "1K", "16:9", out)
    meta = {"provider": provider, "model": all_providers()[provider]["model"],
            "label": all_providers()[provider]["label"],
            "subject": subject or None,
            "style_anchors": [r["id"] for r in style_refs],
            "notes": notes[:500], "created_at": store.utcnow()}
    store._atomic_write_json(_samples_dir() / f"{provider}.json", meta)
    return meta


def list_samples() -> list[dict]:
    out = []
    for provider, cfg in PROVIDERS.items():
        meta_p = _samples_dir() / f"{provider}.json"
        img_p = _samples_dir() / f"{provider}.png"
        meta = (json.loads(meta_p.read_text(encoding="utf-8"))
                if meta_p.exists() else {"provider": provider, "label": cfg["label"],
                                         "model": cfg["model"]})
        meta["has_image"] = img_p.exists()
        out.append(meta)
    return out


def sample_image_path(provider: str) -> Path | None:
    p = _samples_dir() / f"{provider}.png"
    return p if p.exists() else None


# ------------------------------------------------------------- region repair

REPAIR_PROVIDERS = {"openai", "gemini"}  # openai-chat has no masked-edit path


def repair_region(spec_id: str, cand_id: str, mask_png: bytes,
                  instruction: str, ref_ids: list[str] | None = None,
                  provider: str = "openai") -> dict:
    """Painted-mask fix (M7): regenerate ONLY the masked region of a candidate,
    optionally anchored by references. The mask PNG must match the source image
    dimensions, transparent where the repair goes. The engine supplies only
    the patch: its output is composited back into the ORIGINAL image, so
    pixels outside the mask are carried over bit-identical — provider
    re-encoding can never touch them (user-confirmed artifact source,
    2026-07-30). OpenAI paints from a true mask; Gemini from a
    magenta-highlighted guide copy."""
    from common import stable_hash
    from PIL import Image
    import io

    if provider not in REPAIR_PROVIDERS and not (
            provider == "mock" and mock_enabled()):
        raise GenerationError(
            f"repair provider must be one of {sorted(REPAIR_PROVIDERS)}")
    instruction = (instruction or "").strip()
    if not instruction:
        raise GenerationError("describe what should change in the masked region")
    src = get_candidate(spec_id, cand_id)
    if src is None:
        raise KeyError(cand_id)
    src_path = candidate_image_path(spec_id, cand_id)
    if src_path is None:
        raise GenerationError(f"image file missing for {cand_id}")

    refs = []
    for rid in (ref_ids or []):
        r = store.get_reference(rid)
        if r is None:
            raise KeyError(f"unknown reference: {rid}")
        if r["status"] != "APPROVED":
            raise GenerationError(f"{rid} is not APPROVED")
        refs.append(r)

    src_im = guide_im = None
    with Image.open(io.BytesIO(mask_png)) as m, Image.open(src_path) as s:
        src_w, src_h = s.size
        if m.size != s.size:
            raise GenerationError(
                f"mask is {m.size[0]}x{m.size[1]} but the image is "
                f"{s.size[0]}x{s.size[1]} — they must match")
        if provider == "gemini":
            src_im = s.convert("RGB")
            # Mask is opaque where the image stays, transparent where the
            # repair goes — turn that hole into a visible magenta highlight.
            hole = m.convert("RGBA").getchannel("A").point(
                lambda a: 255 if a < 128 else 0)
            tint = Image.blend(src_im, Image.new("RGB", src_im.size,
                                                 (255, 0, 255)), 0.55)
            guide_im = Image.composite(tint, src_im, hole)

    idents = []
    for s_rec in store.list_subjects():
        if s_rec["name"].casefold() in instruction.casefold() and (
                s_rec.get("traits") or s_rec.get("subtitle")):
            idents.append(f"- {s_rec['name']} ({s_rec['kind']}): "
                          + " ".join([s_rec.get("subtitle", "")]
                                     + s_rec.get("traits", [])).strip())

    if provider == "gemini":
        lines = [
            "REGION REPAIR — targeted edit of an existing production render.",
            "The FIRST attached image is the source render. The SECOND is the "
            "same render with the repair region highlighted in magenta — the "
            "magenta is a location guide ONLY and must never appear in your "
            "output.",
            "Reproduce the source render EXACTLY — same composition, content, "
            "light, and paint style — changing ONLY what lies inside the "
            "highlighted region. The change must blend seamlessly with its "
            "surroundings.",
        ]
        refs_head = ("ATTACHED REFERENCES (after the source and guide images) "
                     "— each controls only its role:")
    else:
        lines = [
            "REGION REPAIR — masked edit of an existing production render.",
            "Edit ONLY the masked (transparent) region. Everything outside it "
            "must remain EXACTLY as it is — same content, same light, same "
            "paint style. The repair must blend seamlessly with its "
            "surroundings.",
        ]
        refs_head = ("ATTACHED REFERENCES (after the source image) — each "
                     "controls only its role:")
    lines += ["", "CHANGE REQUESTED", instruction]
    if idents:
        lines += ["", "SUBJECT IDENTITIES — render exactly, never a generic "
                  "substitute:"] + idents
    if refs:
        lines += ["", refs_head]
        lines += [f"- {r['id']}: {r['role']}" for r in refs]
    prompt = "\n".join(lines)

    ref_paths = _reference_image_paths(refs)
    new_id = _new_candidate_id()
    d = _spec_board_dir(spec_id)
    out_path = d / f"{new_id}.png"
    notes = ""

    if provider == "mock":
        # A visibly-different patch; the mask composite below still carries
        # every outside-mask pixel over bit-identical.
        mockflow.repair_patch(src_path, out_path)
        notes = mockflow.NOTES
        model_used = mockflow.MODEL_NAME
    elif provider == "gemini":
        from google.genai import types

        contents: list = [prompt, src_im, guide_im]
        for p in ref_paths:
            _im = Image.open(p)
            _im.load()  # release the handle before the long model call
            contents.append(_im)
        cfg = {"response_modalities": ["TEXT", "IMAGE"]}
        # Gemini's ImageConfig only accepts its own enum — a film-format
        # source (e.g. 2.55:1 from GPT Image 2) repairs without a size hint.
        if src.get("image_size") in IMAGE_SIZES \
                and src.get("aspect_ratio") in GEMINI_RATIOS:
            cfg["image_config"] = types.ImageConfig(
                aspect_ratio=src["aspect_ratio"],
                image_size=src["image_size"])
        try:
            response = _client().models.generate_content(
                model=MODEL, contents=contents,
                config=types.GenerateContentConfig(**cfg))
        except Exception as e:
            raise GenerationError(f"region repair failed: {e}") from e
        image_part, note_text = None, []
        for part in (response.parts or []):
            if getattr(part, "text", None):
                note_text.append(part.text)
            elif part.as_image() is not None:
                image_part = part.as_image()
        if image_part is None:
            raise GenerationError(
                "Gemini returned no image for the repair. "
                + (" ".join(note_text)[:500] or "No details provided."))
        image_part.save(out_path)
        notes = " ".join(note_text)[:2000]
        model_used = MODEL
    else:
        import base64

        client = _openai_client()
        files = [src_path.open("rb")]
        files += [p.open("rb") for p in ref_paths]
        try:
            # Request the source's own resolution: without a size the
            # provider returns its ~1.6MP default, so every repair pass was
            # silently downscaling AND re-encoding the whole canvas — the
            # compounding texture-mush artifact of chained repairs.
            response = client.images.edit(
                model=OPENAI_MODEL, image=files if len(files) > 1 else files[0],
                mask=("mask.png", mask_png, "image/png"),
                prompt=prompt, quality="high",
                size=legal_openai_size(src_w, src_h))
        except Exception as e:
            raise GenerationError(f"region repair failed: {e}") from e
        finally:
            for f in files:
                f.close()
        if not getattr(response, "data", None) or not response.data[0].b64_json:
            raise GenerationError("OpenAI returned no image for the repair.")
        out_path.write_bytes(base64.b64decode(response.data[0].b64_json))
        model_used = OPENAI_MODEL

    # THE MASK IS ENFORCED HERE, NOT TRUSTED THERE (user-confirmed 2026-07-30:
    # the masked edit itself introduces speckle/crackle — the API re-encodes
    # every pixel of the canvas, mask or no mask). So the model only supplies
    # the painted region: its output is composited into the ORIGINAL image,
    # and every pixel outside your paint is carried over bit-identical. A
    # feathered edge blends the seam. Applies to both engines — this also
    # hard-clips Gemini's guided-edit drift outside the region.
    from PIL import ImageFilter
    with Image.open(out_path) as patch_img, Image.open(src_path) as src_img, \
            Image.open(io.BytesIO(mask_png)) as m2:
        src_rgb = src_img.convert("RGB")
        patch = patch_img.convert("RGB")
        if patch.size != src_rgb.size:
            patch = patch.resize(src_rgb.size, Image.LANCZOS)
        hole = m2.convert("RGBA").getchannel("A").point(
            lambda a: 255 if a < 128 else 0)
        hole = hole.filter(ImageFilter.GaussianBlur(6))
        composed = Image.composite(patch, src_rgb, hole)
        composed.save(out_path)

    with Image.open(out_path) as im:
        width, height = im.size

    spec = store.get_spec(spec_id) or {}
    record = {
        "candidate_id": new_id,
        "specification_id": spec_id,
        "spec_hash": stable_hash(spec) if spec else src.get("spec_hash", ""),
        "panel_id": src.get("panel_id", ""),
        "kind": "repair",
        "repaired_from": cand_id,
        "status": "CANDIDATE",
        "provider": provider,
        "model": model_used,
        "warnings": [],
        "image_size": src.get("image_size", "-"),
        "aspect_ratio": src.get("aspect_ratio", "-"),
        "width": width, "height": height,
        "references": [{"id": r["id"], "role": r["role"],
                        "sha256": r.get("sha256", "")} for r in refs],
        "prompt": prompt,
        "model_notes": (f"region repair of {cand_id} — outside-mask pixels "
                        "carried over from the source unchanged (composited)"
                        + (f" — {notes}" if notes else "")),
        "created_at": store.utcnow(),
    }
    (d / f"{new_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def nearest_catalog_aspect(width: int, height: int) -> str:
    value = width / max(1, height)
    return min(ASPECT_CATALOG,
               key=lambda a: abs(aspect_value(a["id"]) - value))["id"]


RERENDER_PROMPT = """FULL-FIDELITY RE-RENDER of an approved production take.
Reproduce the attached source image EXACTLY — same composition, same contents,
same light, same palette, same paint handling — at full output resolution.
This is a re-performance for resolution, not a variation: add no objects,
remove none, reinterpret nothing. Where the small source could not hold
detail, render that detail truthfully within the forms it already shows —
never invent new content to fill space.

DAMAGE IS NOT CONTENT: the source is a small, generation-degraded file. Its
compression noise, speckle, white dot sparkle, crackle, embossed or
fingerprint-like repetition, and any dense repeating micro-pattern are file
damage — do NOT reproduce them. Repaint those regions as clean, coherent,
readable surfaces: ground reads as ground, grass as grass, in large value
shapes. Texture only where it states material, scale, or wear."""


def rerender_full(spec_id: str, cand_id: str, image_size: str = "4K",
                  provider: str = "openai") -> dict:
    """Re-performance for resolution: the take is fed to the engine as its
    own sole anchor with a locked reproduce-exactly instruction and rendered
    at the requested size. Detail is re-synthesized, never interpolated —
    this is the sanctioned answer to a good take trapped at low resolution
    (the no-upscaling rule stands). Lineage recorded as kind: rerender."""
    from common import stable_hash
    from PIL import Image

    if provider not in ("gemini", "openai") and not (
            provider == "mock" and mock_enabled()):
        raise GenerationError("re-render supports gemini or openai — the "
                              "source image is the only anchor either gets")
    if image_size not in IMAGE_SIZES:
        raise GenerationError(f"image_size must be one of {sorted(IMAGE_SIZES)}")
    src = get_candidate(spec_id, cand_id)
    if src is None:
        raise KeyError(cand_id)
    src_path = candidate_image_path(spec_id, cand_id)
    if src_path is None:
        raise GenerationError(f"image file missing for {cand_id}")
    with Image.open(src_path) as im:
        src_w, src_h = im.size
    aspect = nearest_catalog_aspect(src_w, src_h)

    new_id = _new_candidate_id()
    d = _spec_board_dir(spec_id)
    out_path = d / f"{new_id}.png"
    notes = ""

    if provider == "mock":
        notes = mockflow.render(RERENDER_PROMPT, [src_path], image_size,
                                aspect, out_path)
        model_used = mockflow.MODEL_NAME
    elif provider == "openai":
        import base64
        client = _openai_client()
        with src_path.open("rb") as f:
            try:
                response = client.images.edit(
                    model=OPENAI_MODEL, image=f, prompt=RERENDER_PROMPT,
                    quality="high", size=openai_size(image_size, aspect))
            except Exception as e:
                raise GenerationError(f"re-render failed: {e}") from e
        if not getattr(response, "data", None) or not response.data[0].b64_json:
            raise GenerationError("OpenAI returned no image for the re-render.")
        out_path.write_bytes(base64.b64decode(response.data[0].b64_json))
        model_used = OPENAI_MODEL
    else:
        from google.genai import types
        with Image.open(src_path) as s:
            src_im = s.convert("RGB")
        cfg = {"response_modalities": ["TEXT", "IMAGE"]}
        if aspect in GEMINI_RATIOS:
            cfg["image_config"] = types.ImageConfig(
                aspect_ratio=aspect, image_size=image_size)
        try:
            response = _client().models.generate_content(
                model=MODEL, contents=[RERENDER_PROMPT, src_im],
                config=types.GenerateContentConfig(**cfg))
        except Exception as e:
            raise GenerationError(f"re-render failed: {e}") from e
        image_part, note_text = None, []
        for part in (response.parts or []):
            if getattr(part, "text", None):
                note_text.append(part.text)
            elif part.as_image() is not None:
                image_part = part.as_image()
        if image_part is None:
            raise GenerationError("Gemini returned no image for the re-render. "
                                  + (" ".join(note_text)[:500] or ""))
        image_part.save(out_path)
        notes = " ".join(note_text)[:2000]
        model_used = MODEL

    with Image.open(out_path) as im:
        width, height = im.size
    warnings = []
    if width <= src_w and height <= src_h:
        warnings.append(
            f"re-render returned {width}x{height} — no larger than the "
            f"{src_w}x{src_h} source; try the other engine or 4K")

    spec = store.get_spec(spec_id) or {}
    record = {
        "candidate_id": new_id,
        "specification_id": spec_id,
        "spec_hash": stable_hash(spec) if spec else src.get("spec_hash", ""),
        "panel_id": src.get("panel_id", ""),
        "kind": "rerender",
        "rerendered_from": cand_id,
        "status": "CANDIDATE",
        "provider": provider,
        "model": model_used,
        "image_size": image_size,
        "aspect_ratio": aspect,
        "width": width, "height": height,
        "warnings": warnings,
        "references": [],
        "prompt": RERENDER_PROMPT,
        "model_notes": (f"full-fidelity re-render of {cand_id} "
                        f"({src_w}x{src_h} source)" + (f" — {notes}" if notes else "")),
        "created_at": store.utcnow(),
    }
    (d / f"{new_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def generate_panel(spec_id: str, panel_id: str, ref_ids: list[str],
                   image_size: str = "2K", aspect_ratio: str = "16:9",
                   provider: str = DEFAULT_PROVIDER,
                   render_prompt: str = "") -> dict:
    from common import stable_hash
    from PIL import Image

    if image_size not in IMAGE_SIZES:
        raise GenerationError(f"image_size must be one of {sorted(IMAGE_SIZES)}")
    if aspect_ratio not in ASPECT_RATIOS:
        raise GenerationError(f"aspect_ratio must be one of {sorted(ASPECT_RATIOS)}")
    providers = all_providers()
    if provider not in providers:
        raise GenerationError(f"provider must be one of {sorted(providers)}")
    # Ratios are enforced per engine's real contract — never approximated.
    if provider == "gemini" and aspect_ratio not in GEMINI_RATIOS:
        raise GenerationError(
            f"Gemini cannot render {aspect_ratio} — its API accepts a fixed "
            "set of ratios. Use GPT Image 2 or a custom engine for film formats.")
    if provider == "openai-chat" and aspect_ratio not in CHAT_RATIOS:
        raise GenerationError(
            f"The ChatGPT pipeline cannot render {aspect_ratio} — its image "
            "tool has three preset sizes (1:1, 3:2, 2:3). Pick one of those "
            "or a direct engine.")
    if provider.startswith(("or:", "fal:")):
        enum = providers[provider].get("aspect_enum")
        if enum and aspect_ratio not in enum:
            raise GenerationError(
                f"{providers[provider]['label']} states a fixed aspect set "
                f"({', '.join(enum)}) — pick one of those.")

    spec, panel, refs = _resolve_generation_inputs(spec_id, panel_id, ref_ids)
    prompt = compile_panel_prompt(spec, panel, refs)
    ref_paths = _reference_image_paths(refs)
    override = (render_prompt or "").strip()

    cand_id = store.next_counter("cand_counter", "CAND")

    d = _spec_board_dir(spec_id)
    img_path = d / f"{cand_id}.png"
    if provider == "mock":
        notes = mockflow.render(override or prompt, ref_paths, image_size,
                                aspect_ratio, img_path)
    elif provider == "openai-chat":
        # A user-edited prompt is final copy: skip the rewrite, render it as-is.
        notes = _render_openai_chat(override or prompt, ref_paths, image_size,
                                    aspect_ratio, img_path, verbatim=bool(override))
    elif provider.startswith("custom:"):
        notes = _render_custom(provider, override or prompt, ref_paths,
                               image_size, aspect_ratio, img_path)
    elif provider.startswith(("or:", "fal:")):
        notes = _render_connector(provider, override or prompt, ref_paths,
                                  image_size, aspect_ratio, img_path)
    else:
        render = _render_openai if provider == "openai" else _render_gemini
        notes = render(override or prompt, ref_paths, image_size, aspect_ratio, img_path)
    with Image.open(img_path) as im:
        width, height = im.size

    record = {
        "candidate_id": cand_id,
        "specification_id": spec_id,
        "spec_hash": stable_hash(spec),
        "panel_id": panel_id,
        "status": "CANDIDATE",
        "provider": provider,
        "model": providers[provider]["model"],
        "image_size": image_size,
        "aspect_ratio": aspect_ratio,
        "width": width,
        "height": height,
        "references": [{"id": r["id"], "role": r["role"], "sha256": r["sha256"]} for r in refs],
        "prompt": prompt,
        "prompt_source": "edited" if override else "spec",
        "model_notes": notes,
        "created_at": store.utcnow(),
    }
    if override:
        # The compiled spec prompt above stays the canonical governance record;
        # this is the exact text the image model was actually given.
        record["render_prompt"] = override
    (d / f"{cand_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def mark_promoted(spec_id: str, cand_id: str, ref_id: str) -> None:
    """Back-link a promoted take to the reference it became, so the judging
    room can badge it."""
    record = get_candidate(spec_id, cand_id)
    if record is None:
        return
    record["promoted_ref"] = ref_id
    (paths.BOARDS_DIR / spec_id / f"{cand_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def delete_candidate(spec_id: str, cand_id: str) -> dict:
    """Permanently delete a rejected candidate's image and record. Guarded:
    only REJECTED candidates can be deleted — reject first, then delete. The
    deletion is logged to the rejection history so the trail survives the file."""
    record = get_candidate(spec_id, cand_id)
    if record is None:
        raise KeyError(cand_id)
    if record["status"] != "REJECTED":
        raise GenerationError(
            f"{cand_id} is {record['status']} — only REJECTED candidates can be "
            "permanently deleted. Reject it first.")

    archive_feedback(spec_id, record.get("panel_id", ""),
                     record.get("status_reason", ""), cand_id)

    line = (f"- {store.utcnow()} — {cand_id} ({spec_id}/{record.get('panel_id', '?')}, "
            f"{record.get('model', 'unknown model')}) permanently deleted. "
            f"Reason: {record.get('status_reason', '—')}\n")
    hist = paths.REJECTION_HISTORY
    header = "" if hist.exists() else "# Rejection History\n\n"
    with hist.open("a", encoding="utf-8") as f:
        f.write(header + line)

    d = paths.BOARDS_DIR / spec_id
    (d / f"{cand_id}.png").unlink(missing_ok=True)
    (d / f"{cand_id}.json").unlink(missing_ok=True)
    return {"deleted": cand_id}


def purge_rejected(spec_id: str) -> dict:
    deleted = []
    for c in list_candidates(spec_id):
        if c.get("status") == "REJECTED":
            delete_candidate(spec_id, c["candidate_id"])
            deleted.append(c["candidate_id"])
    return {"deleted": deleted, "count": len(deleted)}


DERIVED_PANELS = {"PALETTE", "MATERIALS"}


def _approved_panel_candidates(spec_id: str) -> list[dict]:
    return [c for c in list_candidates(spec_id)
            if c.get("status") == "APPROVED"
            and c.get("panel_id") not in DERIVED_PANELS
            and c.get("kind") != "assembled_board"]


def _new_candidate_id() -> str:
    return store.next_counter("cand_counter", "CAND")


def derive_palette(spec_id: str) -> dict:
    """Deterministic palette panel: dominant colors SAMPLED from the board's
    own approved panels — a measurement, not a generation. The board cannot
    disagree with its own palette."""
    from PIL import Image, ImageDraw

    sources = _approved_panel_candidates(spec_id)
    if not sources:
        raise GenerationError(
            "no approved panels to sample — approve at least one panel candidate first.")

    thumbs = []
    for c in sources:
        p = candidate_image_path(spec_id, c["candidate_id"])
        if p is None:
            continue
        with Image.open(p) as im:
            im = im.convert("RGB")
            im.thumbnail((512, 512))
            thumbs.append(im.copy())
    if not thumbs:
        raise GenerationError("approved panel images missing on disk.")

    strip_w = sum(t.width for t in thumbs)
    strip_h = max(t.height for t in thumbs)
    composite = Image.new("RGB", (strip_w, strip_h))
    x = 0
    for t in thumbs:
        composite.paste(t, (x, 0))
        x += t.width

    n_colors = 10
    quant = composite.convert("P", palette=Image.ADAPTIVE, colors=n_colors)
    palette = quant.getpalette()
    counts = sorted(quant.getcolors(maxcolors=n_colors * 2) or [], reverse=True)
    swatches = []
    for count, idx in counts[:n_colors]:
        r, g, b = palette[idx * 3: idx * 3 + 3]
        swatches.append((count, (r, g, b)))
    if not swatches:
        raise GenerationError("could not extract a palette from the approved panels.")

    w, h, label_h = 2400, 420, 90
    sw = w // len(swatches)
    out = Image.new("RGB", (w, h), (20, 20, 22))
    draw = ImageDraw.Draw(out)
    for i, (_, rgb) in enumerate(swatches):
        x0 = i * sw
        draw.rectangle([x0, 0, x0 + sw - 4, h - label_h], fill=rgb)
        hexcode = "#{:02X}{:02X}{:02X}".format(*rgb)
        draw.text((x0 + 12, h - label_h + 18), hexcode, fill=(232, 229, 221))

    cand_id = _new_candidate_id()
    d = _spec_board_dir(spec_id)
    out.save(d / f"{cand_id}.png")

    from common import stable_hash
    spec = store.get_spec(spec_id) or {}
    record = {
        "candidate_id": cand_id,
        "specification_id": spec_id,
        "spec_hash": stable_hash(spec) if spec else "",
        "panel_id": "PALETTE",
        "kind": "derived_palette",
        "status": "CANDIDATE",
        "provider": "deterministic",
        "model": "palette-sampler (no AI — colors measured from approved panels)",
        "image_size": "-", "aspect_ratio": "-",
        "width": w, "height": h,
        "references": [{"id": c["candidate_id"], "role": "PALETTE_SOURCE",
                        "sha256": ""} for c in sources],
        "prompt": "",
        "model_notes": "Dominant colors sampled from: "
                       + ", ".join(c["candidate_id"] for c in sources),
        "created_at": store.utcnow(),
    }
    (d / f"{cand_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def derive_materials(spec_id: str, provider: str = DEFAULT_PROVIDER,
                     image_size: str = "2K") -> dict:
    """Generated materials panel, anchored to the board's own approved
    imagery: the timber in the strip is THIS cabin's timber."""
    from common import stable_hash
    from PIL import Image

    providers = all_providers()
    if provider not in providers:
        raise GenerationError(f"provider must be one of {sorted(providers)}")
    sources = _approved_panel_candidates(spec_id)
    if not sources:
        raise GenerationError(
            "no approved panels to derive from — approve at least one panel candidate first.")
    spec = store.get_spec(spec_id)
    if spec is None:
        raise KeyError(spec_id)

    src_paths = []
    for c in sources:
        p = candidate_image_path(spec_id, c["candidate_id"])
        if p:
            src_paths.append(p)
    src_paths = src_paths[:MAX_REFERENCE_IMAGES]

    fake_panel = {"id": "MATERIALS", "title": "Materials strip",
                  "purpose": "Material and texture studies derived from this board's "
                             "approved panels."}
    prompt = "\n".join([
        f"{store.project_name().upper()} PRODUCTION RENDER — DERIVED MATERIALS PANEL",
        f"SPECIFICATION: {spec_id} (hash {stable_hash(spec)[:16]})",
        "",
        "TASK",
        "Create ONE full-bleed materials study strip: 4-6 close-up material and "
        "texture studies of surfaces VISIBLE in the attached approved panels of "
        "this board — the same wood, the same metal, the same weathering and age. "
        "Arranged side by side like a physical materials board. No new objects, "
        "no scene, no figures, no text or labels.",
        "",
        "SOURCE RULE",
        "Every material must come from the attached panels. Do not invent "
        "materials the panels do not show.",
        "",
        _style_context(spec, fake_panel),
        "",
        "ATTACHED IMAGES",
        "Each attached image is an approved panel of this board (role "
        "MATERIAL_SOURCE): it controls which materials, surfaces, and weathering "
        "exist. It does not control composition — this is a swatch strip, not a "
        "scene.",
    ])

    cand_id = _new_candidate_id()
    d = _spec_board_dir(spec_id)
    img_path = d / f"{cand_id}.png"
    if provider == "mock":
        notes = mockflow.render(prompt, src_paths, image_size, "21:9", img_path)
    elif provider == "openai-chat":
        notes = _render_openai_chat(prompt, src_paths, image_size, "21:9", img_path,
                                    verbatim=True)
    elif provider == "openai":
        notes = _render_openai(prompt, src_paths, image_size, "21:9", img_path)
    elif provider.startswith("custom:"):
        notes = _render_custom(provider, prompt, src_paths, image_size, "21:9", img_path)
    else:
        notes = _render_gemini(prompt, src_paths, image_size, "21:9", img_path)
    with Image.open(img_path) as im:
        width, height = im.size

    record = {
        "candidate_id": cand_id,
        "specification_id": spec_id,
        "spec_hash": stable_hash(spec),
        "panel_id": "MATERIALS",
        "kind": "derived_materials",
        "status": "CANDIDATE",
        "provider": provider,
        "model": providers[provider]["model"],
        "image_size": image_size, "aspect_ratio": "21:9",
        "width": width, "height": height,
        "references": [{"id": c["candidate_id"], "role": "MATERIAL_SOURCE",
                        "sha256": ""} for c in sources],
        "prompt": prompt,
        "model_notes": notes,
        "created_at": store.utcnow(),
    }
    (d / f"{cand_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


def create_lighting_study(spec_id: str, cand_id: str,
                          atmospheres: list[str] | None = None) -> dict:
    """Derive a lighting-study board from an approved panel: the panel is
    promoted to a LOCATION_GEOMETRY anchor, and each study panel renders the
    same place under one approved atmosphere."""
    parent = store.get_spec(spec_id)
    if parent is None:
        raise KeyError(spec_id)
    cand = get_candidate(spec_id, cand_id)
    if cand is None:
        raise KeyError(cand_id)
    if cand.get("status") != "APPROVED":
        raise GenerationError(
            f"{cand_id} is {cand.get('status')} — only an APPROVED panel can anchor "
            "a lighting study.")
    img = candidate_image_path(spec_id, cand_id)
    if img is None:
        raise GenerationError(f"image file missing for {cand_id}")

    atmos = [a.strip() for a in (atmospheres or bible.atmospheres()) if a.strip()][:8]
    if not atmos:
        raise GenerationError(
            "no atmospheres available — the Art Direction Bible's Lighting Language "
            "has no approved atmosphere studies to draw from.")

    ref = store.add_reference(
        f"{cand_id} geometry ({spec_id}).png", img.read_bytes(), "LOCATION_GEOMETRY",
        ["location geometry, structure, layout, composition"],
        ["lighting, palette, atmosphere, time of day, weather"],
        notes=f"geometry anchor promoted from {cand_id} of {spec_id}")
    ref = store.set_reference_status(ref["id"], "APPROVED")

    base = re.sub(r"_R\d+$", "", spec_id)
    study_id = f"{base}_LIGHT"
    n = 1
    while store.get_spec(f"{study_id}_V{n:03d}") is not None:
        n += 1
    study_id = f"{study_id}_V{n:03d}"

    study = store.new_spec(study_id, f"Lighting study — {parent.get('subject', spec_id)}",
                           "DESIGN_EXPLORATION")
    study["board_type"] = "LIGHTING_STUDY"
    study["setting"] = dict(parent.get("setting") or {})
    study["setting"].pop("time_of_day", None)
    study["scene"] = parent.get("scene", "")
    study["geometry_ref"] = ref["id"]
    study["derived_from"] = {"specification_id": spec_id, "candidate_id": cand_id}
    study["render_intent"] = ("Lighting study series: identical location, geometry, "
                              "and composition in every panel — only light, palette, "
                              "and atmosphere change.")
    if "design_languages" in parent:
        study["design_languages"] = list(parent["design_languages"])
        study["scene_lessons"] = list(parent.get("scene_lessons", []))
    # A study lives in its parent's world — environments inherit alongside
    # languages (plan P8).
    if parent.get("environments"):
        study["environments"] = list(parent["environments"])
    panels, layout = [], []
    share = round(100.0 / len(atmos), 2)
    for i, a in enumerate(atmos, 1):
        pid = f"P{i:02d}"
        panels.append({
            "id": pid, "title": a[:120],
            "purpose": (f"Lighting study: the anchor location under \"{a}\". Same "
                        "place, same camera; only the light changes."),
            "required_objects": [], "forbidden_objects": [],
            "evidence": ["USER_DIRECTED"], "scale": "WIDE",
            "composition_role": "lighting study",
            "time_of_day": a,
        })
        layout.append({"id": pid, "allocation_percent": share})
    layout[0]["allocation_percent"] = round(100.0 - share * (len(atmos) - 1), 2)
    study["panels"] = panels
    study["layout"] = {"canvas": "lighting study strip", "panels": layout}
    store.save_spec(study_id, study)
    return study


def set_candidate_status(spec_id: str, cand_id: str, status: str, reason: str = "") -> dict:
    if status not in CANDIDATE_STATUSES:
        raise GenerationError(f"invalid status: {status}")
    record = get_candidate(spec_id, cand_id)
    if record is None:
        raise KeyError(cand_id)
    record["status"] = status
    if reason:
        record["status_reason"] = reason
        # Rejection reasons surface as REJECTION FEEDBACK directives on this
        # panel's future prompts (see rejection_feedback) — NOT as global
        # never-include lessons, which inverted directive-style feedback.
        # Project-wide rules are curated by hand in Settings.
    record["updated_at"] = store.utcnow()
    d = paths.BOARDS_DIR / spec_id
    (d / f"{cand_id}.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if status == "APPROVED":
        store.append_approval_log(
            f"PANEL CANDIDATE {cand_id} ({spec_id} / {record['panel_id']}) approved. "
            f"Spec hash {record['spec_hash'][:16]}…")
    return record
