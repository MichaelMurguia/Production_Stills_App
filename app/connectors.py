from __future__ import annotations

"""Provider connectors (CONNECTORS_PLAN N1): one user-owned credential
unlocks a self-updating catalog of image models.

The registry names the connectors; the state file (install-level,
HOME/connectors.json — keys follow the user across productions exactly
like settings.json) holds each connector's credential, synced catalog,
enabled set and witnessed previews. Adapters do the provider-specific
work and take an injected `http` callable so tests drive the whole
machine with fakes — the provisioner's pattern.

Model record (internal, OpenRouter-aligned):
  id                 "or:openai/gpt-image-2" | "fal:fal-ai/flux-2/dev"
  connector          "openrouter" | "fal"
  provider_model_id  the connector's native id / endpoint_id
  label, developer
  task               "text-to-image" | "image-to-image"
  refs               True when the model accepts image input
  max_refs           int — OUR pipeline cap unless the provider states less
  max_px             longest-edge native ceiling; None = catalog silent
  aspect_enum        list of ratio strings when the catalog states one
  price_per_image    decimal string when the catalog states one; None never invented
  status             "active" | "deprecated"
  supported          False = parameter shape not yet mapped (listed, not enableable)
"""

import datetime as dt
import json
import urllib.error
import urllib.parse
import urllib.request

from . import paths, store

# Our pipeline's reference ceiling — mirrored from generate.py to avoid a
# circular import; generate imports us, not the reverse.
APP_MAX_REFS = 14


def _state_file():
    return paths.HOME / "connectors.json"


def cache_dir():
    return paths.HOME / "connectors-cache"


REGISTRY = {
    "openrouter": {
        "label": "OpenRouter",
        "tile": "ORT",
        "auth": "oauth",  # one-click PKCE; the scoped key IS stored here
        "key_page": "https://openrouter.ai/settings/keys",
        "prices_published": True,
    },
    "fal": {
        "label": "fal.ai",
        "tile": "FAL",
        "auth": "key",
        "key_page": "https://fal.ai/dashboard/keys",
        "prices_published": False,
    },
}

# Courier initials tiles for developers seen in catalogs (C6). Unknown
# developers get a derived two/three-letter tile, never a broken image.
DEV_TILES = {
    "openai": "OAI", "google": "GGL", "black forest labs": "BFL",
    "bytedance": "BDN", "ideogram": "IDG", "recraft": "RCF",
    "stability": "STB", "higgsfield": "HGS", "x-ai": "XAI", "xai": "XAI",
    "microsoft": "MSF", "krea": "KRA", "qwen": "QWN", "alibaba": "QWN",
}


class ConnectorError(Exception):
    pass


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state() -> dict:
    f = _state_file()
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            f.replace(f.with_suffix(".json.corrupt"))
    return {}


def save_state(state: dict) -> None:
    paths.HOME.mkdir(parents=True, exist_ok=True)
    store._atomic_write_json(_state_file(), state)


def _http_json(url: str, method: str = "GET", headers: dict | None = None,
               body: dict | None = None, timeout: int = 60) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def dev_tile(developer: str) -> str:
    d = (developer or "").strip().lower()
    if d in DEV_TILES:
        return DEV_TILES[d]
    letters = [w[0] for w in d.replace("-", " ").split() if w][:3]
    return ("".join(letters).upper() or "???")


# ------------------------------------------------------------- state model
# Connector row states (C2): NOT CONNECTED / SYNCED / REJECTED / NO NETWORK.
# The stored record only keeps facts (key, last_sync, last_error kind);
# the row state is derived so it can never drift from them.

def connector_public(cid: str, state: dict | None = None) -> dict:
    state = state if state is not None else load_state()
    meta = REGISTRY[cid]
    c = state.get(cid, {})
    key = c.get("key", "")
    catalog = c.get("catalog", [])
    enabled = set(c.get("enabled", []))
    err = c.get("last_error") or {}
    if not key:
        status = "NOT_CONNECTED"
    elif err.get("kind") == "auth":
        status = "REJECTED"
    elif err.get("kind") == "network":
        status = "NO_NETWORK"
    else:
        status = "SYNCED"
    return {
        "id": cid, "label": meta["label"], "tile": meta["tile"],
        "auth": meta["auth"], "key_page": meta["key_page"],
        "prices_published": meta["prices_published"],
        "status": status,
        "key_hint": (key[:4] + "…" + key[-4:]) if key else "",
        "identity": c.get("identity", ""),
        "model_count": len(catalog),
        "enabled_count": sum(1 for m in catalog if m["id"] in enabled),
        "last_sync": c.get("last_sync", ""),
        "last_error": err,
    }


def catalog_records(state: dict | None = None) -> list[dict]:
    """Every synced record across connectors, enabled flag attached."""
    state = state if state is not None else load_state()
    out = []
    for cid in REGISTRY:
        c = state.get(cid, {})
        enabled = set(c.get("enabled", []))
        for m in c.get("catalog", []):
            out.append({**m, "enabled": m["id"] in enabled})
    return out


def enabled_records(state: dict | None = None) -> list[dict]:
    return [m for m in catalog_records(state) if m["enabled"]]


def filter_records(records: list[dict], query: str = "",
                   refs_only: bool = False, fourk_only: bool = False,
                   priced_only: bool = False) -> list[dict]:
    q = (query or "").strip().lower()
    out = []
    for m in records:
        if refs_only and not m.get("refs"):
            continue
        if fourk_only and not (m.get("max_px") and m["max_px"] >= 3840):
            continue
        if priced_only and not m.get("price_per_image"):
            continue
        if q and q not in " ".join([
                m.get("label", ""), m.get("developer", ""),
                m.get("provider_model_id", "")]).lower():
            continue
        out.append(m)
    return out


def set_enabled(model_id: str, on: bool) -> dict:
    """Enable/disable a catalog model. Unsupported shapes are not
    enableable — stated upstream, enforced here."""
    state = load_state()
    for cid in REGISTRY:
        c = state.get(cid, {})
        rec = next((m for m in c.get("catalog", []) if m["id"] == model_id), None)
        if rec is None:
            continue
        if on and not rec.get("supported", True):
            raise ConnectorError(
                f"{rec['label']}: parameter shape not yet mapped — cannot enable.")
        enabled = set(c.get("enabled", []))
        (enabled.add if on else enabled.discard)(model_id)
        c["enabled"] = sorted(enabled)
        state[cid] = c
        save_state(state)
        return {**rec, "enabled": on}
    raise ConnectorError(f"unknown catalog model: {model_id}")


def disconnect(cid: str) -> None:
    """Forget the credential. The catalog cache and enabled set are kept —
    reconnecting must not lose the user's curation; enabled models render
    only when a working credential returns."""
    state = load_state()
    c = state.get(cid, {})
    for k in ("key", "identity", "pkce_verifier"):
        c.pop(k, None)
    c["last_error"] = {}
    state[cid] = c
    save_state(state)


def stats(state: dict | None = None) -> dict:
    """The §03 tiles (C4) — the single source both the summary and the
    browser count read from."""
    records = catalog_records(state)
    enabled = [m for m in records if m["enabled"]]
    return {
        "total": len(records),
        "enabled": len(enabled),
        "anchor_refs": sum(1 for m in enabled if m.get("refs")),
        "fourk": sum(1 for m in enabled if (m.get("max_px") or 0) >= 3840),
        "deprecated_enabled": sum(1 for m in enabled if m.get("status") != "active"),
    }


def _record_error(state: dict, cid: str, kind: str, detail: str) -> None:
    c = state.setdefault(cid, {})
    c["last_error"] = {"kind": kind, "detail": detail[:300], "at": now_iso()}
    save_state(state)


def _classify(e: Exception) -> str:
    if isinstance(e, urllib.error.HTTPError) and e.code in (401, 403):
        return "auth"
    return "network"


# ---------------------------------------------------------- OpenRouter (N3)
# Catalog: GET /api/v1/models?output_modalities=image — architecture
# modalities, per-image pricing. Key test/identity: GET /api/v1/key.
# Generation: chat completions with modalities ["image","text"]; refs ride
# as data-URI image parts; the image returns base64 in message.images.

OPENROUTER_API = "https://openrouter.ai/api/v1"


def _or_headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://www.screenboardstudio.com",
            "X-Title": "Screenboard Studio"}


def _or_normalize(m: dict) -> dict:
    arch = m.get("architecture") or {}
    inputs = [s.lower() for s in arch.get("input_modalities") or []]
    refs = "image" in inputs
    pricing = m.get("pricing") or {}
    price = pricing.get("image_output") or pricing.get("image") or None
    try:
        price = None if not price or float(price) == 0 else f"{float(price):.4f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        price = None
    dev = (m.get("id") or "").split("/")[0]
    # Typed constraints (images/models endpoint): aspect_ratio enum.
    aspect = None
    for pname, spec in (m.get("parameters") or {}).items() if isinstance(m.get("parameters"), dict) else []:
        if pname == "aspect_ratio" and isinstance(spec, dict) and spec.get("enum"):
            aspect = [str(a) for a in spec["enum"]]
    return {
        "id": f"or:{m['id']}",
        "connector": "openrouter",
        "provider_model_id": m["id"],
        "label": m.get("name") or m["id"],
        "developer": dev,
        "task": "image-to-image" if refs else "text-to-image",
        "refs": refs,
        "max_refs": APP_MAX_REFS if refs else 0,
        "max_px": None,  # OpenRouter's catalog states no resolution ceiling
        "aspect_enum": aspect,
        "price_per_image": price,
        "status": "active" if not m.get("deprecated") else "deprecated",
        "supported": True,
    }


def openrouter_sync(key: str, http=None) -> tuple[list[dict], str]:
    """Returns (records, identity). Raises on auth/network failure."""
    http = http or _http_json
    ident = ""
    info = http(f"{OPENROUTER_API}/key", headers=_or_headers(key))
    data = info.get("data") or {}
    ident = data.get("label") or "authorised"
    listing = http(f"{OPENROUTER_API}/models?output_modalities=image",
                   headers=_or_headers(key))
    # The endpoint is already filtered to image-output models.
    records = [_or_normalize(m) for m in listing.get("data") or []]
    return records, ident


# PKCE (one-click connect). The exchanged key is scoped and revocable from
# the user's OpenRouter dashboard — and it IS stored here, because calls
# need it; the UI must say that truthfully (deviation from mock 16b ruled
# at implementation, logged in DESIGN_SYSTEM's changelog).

def pkce_start(callback_url: str) -> str:
    import base64 as b64
    import hashlib
    import secrets
    verifier = secrets.token_urlsafe(48)
    challenge = b64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    state = load_state()
    state.setdefault("openrouter", {})["pkce_verifier"] = verifier
    save_state(state)
    q = urllib.parse.urlencode({
        "callback_url": callback_url,
        "code_challenge": challenge,
        "code_challenge_method": "S256"})
    return f"https://openrouter.ai/auth?{q}"


def pkce_finish(code: str, http=None) -> None:
    http = http or _http_json
    state = load_state()
    verifier = state.get("openrouter", {}).pop("pkce_verifier", "")
    if not verifier:
        raise ConnectorError("No pending connect — start again from Settings.")
    out = http("https://openrouter.ai/api/v1/auth/keys", method="POST", body={
        "code": code, "code_verifier": verifier,
        "code_challenge_method": "S256"})
    key = out.get("key") or ""
    if not key:
        raise ConnectorError("OpenRouter returned no key.")
    state.setdefault("openrouter", {})["key"] = key
    save_state(state)
    sync("openrouter", http=http)


def openrouter_generate(key: str, provider_model_id: str, prompt: str,
                        ref_paths: list, out_path, http=None) -> str:
    """One render through OpenRouter's chat-completions image path.
    References ride as data-URI image parts. No size parameter exists on
    this path — the model renders at its native default and the app's
    no-upscaling flag judges the result honestly."""
    import base64 as b64
    http = http or _http_json
    parts = [{"type": "text", "text": prompt}]
    for p in list(ref_paths)[:APP_MAX_REFS]:
        mime = "image/png" if str(p).lower().endswith(".png") else "image/jpeg"
        parts.append({"type": "image_url", "image_url": {
            "url": f"data:{mime};base64,{b64.b64encode(p.read_bytes()).decode()}"}})
    out = http(f"{OPENROUTER_API}/chat/completions", method="POST",
               headers=_or_headers(key), timeout=600, body={
                   "model": provider_model_id,
                   "messages": [{"role": "user", "content": parts}],
                   "modalities": ["image", "text"]})
    choice = (out.get("choices") or [{}])[0]
    images = (choice.get("message") or {}).get("images") or []
    url = ((images[0].get("image_url") or {}).get("url") or "") if images else ""
    if not url.startswith("data:"):
        detail = (choice.get("message") or {}).get("content") or out.get("error", {}).get("message") or "no image returned"
        raise ConnectorError(f"OpenRouter/{provider_model_id}: {str(detail)[:300]}")
    out_path.write_bytes(b64.b64decode(url.split(",", 1)[1]))
    return ""


def fal_sync(key: str, http=None) -> list[dict]:  # replaced in N4
    raise ConnectorError("fal connector not built yet")


# --------------------------------------------------------------- sync core

def save_key(cid: str, key: str, http=None) -> dict:
    if cid not in REGISTRY:
        raise ConnectorError(f"unknown connector: {cid}")
    state = load_state()
    state.setdefault(cid, {})["key"] = key.strip()
    save_state(state)
    return sync(cid, http=http)


def sync(cid: str, http=None) -> dict:
    """Refresh a connector's catalog. Failures never destroy the cached
    catalog — the last good sync stays browsable with its age stated."""
    state = load_state()
    c = state.setdefault(cid, {})
    key = c.get("key", "")
    if not key:
        raise ConnectorError(f"{REGISTRY[cid]['label']} is not connected.")
    try:
        if cid == "openrouter":
            records, ident = openrouter_sync(key, http=http)
            c["identity"] = ident
        elif cid == "fal":
            records = fal_sync(key, http=http)
        else:
            raise ConnectorError(f"unknown connector: {cid}")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ConnectorError) as e:
        _record_error(state, cid, _classify(e) if not isinstance(e, ConnectorError) else "auth", str(e))
        return connector_public(cid)
    c["catalog"] = records
    c["last_sync"] = now_iso()
    c["last_error"] = {}
    save_state(state)
    return connector_public(cid)
