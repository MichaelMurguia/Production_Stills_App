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
