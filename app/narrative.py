"""Narrative backends beyond OpenAI/Gemini (SETTINGS_FIRST_RUN_PLAN F6's
queued backend, built 2026-08-04): the narrative role — Scene Scan,
breakdown research, bible drafting — can run on the stored Anthropic key
or through the OpenRouter connector, so a customer who connected
OpenRouter (or pasted only a Claude key) gets working narrative passes
instead of a demand for a different credential.

Stdlib HTTP like connectors.py; the http callable is injected for tests.
Both backends take the same shape: a document (the extracted screenplay,
text/plain first — PDF only for image-only scans), instruction text, and
optional reference images; both return (raw_text, model_used).
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

from . import connectors, paths

ANTHROPIC_API = "https://api.anthropic.com/v1"
ANTHROPIC_MODEL = "claude-sonnet-5"      # narrative default; settings can override
OPENROUTER_NARRATIVE_MODEL = "openai/gpt-5.6"  # the first-run notice's promise
# The breakdown draft is a full spec plus an evidence ledger with one cited
# row per object — the app's largest structured output. At 8192 the reply
# was truncated, the whole ~33k-token input was paid for, nothing was
# returned, and the re-run re-sent the screenplay on the one provider where
# that input was uncached (adversarial review F20). Under-spending output
# tokens to save pennies costs a full input pass; the Gemini and OpenAI
# paths set no ceiling at all.
MAX_OUTPUT_TOKENS = 32000


class NarrativeError(Exception):
    pass


def _http_json(url: str, method: str = "GET", headers: dict | None = None,
               body: dict | None = None, timeout: int = 300) -> dict:
    req = urllib.request.Request(
        url, method=method, headers=headers or {},
        data=json.dumps(body).encode() if body is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise NarrativeError(f"{url.split('/')[2]} answered {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise NarrativeError(f"could not reach {url.split('/')[2]}: {e.reason}") from e


# ------------------------------------------------------------- availability

def anthropic_key() -> str:
    from . import generate
    return str(generate.load_settings().get("anthropic_api_key", "")).strip()


def anthropic_model() -> str:
    from . import generate
    return (str(generate.load_settings().get("anthropic_model", "")).strip()
            or ANTHROPIC_MODEL)


def openrouter_key() -> str:
    c = connectors.load_state().get("openrouter") or {}
    return str(c.get("key", "")).strip()


def usable(provider: str) -> bool:
    if provider == "anthropic":
        return bool(anthropic_key())
    if provider == "openrouter":
        return bool(openrouter_key())
    return False


def _mime_of(p) -> str:
    s = str(p).lower()
    return "image/png" if s.endswith(".png") else \
        "image/webp" if s.endswith(".webp") else "image/jpeg"


# ------------------------------------------------------- anthropic (direct)

def anthropic_complete(doc: bytes, mime: str, instructions: str,
                       ref_paths: tuple = (), http=None) -> tuple[str, str]:
    key = anthropic_key()
    if not key:
        raise NarrativeError("no Anthropic key — add one in Settings → AI & engines")
    http = http or _http_json
    model = anthropic_model()
    content: list = []
    if mime == "application/pdf":
        content.append({"type": "document", "source": {
            "type": "base64", "media_type": "application/pdf",
            "data": base64.b64encode(doc).decode()}})
    else:
        content.append({"type": "text",
                        "text": "SCREENPLAY FOLLOWS\n==================\n"
                                + doc.decode("utf-8", "replace")})
    for p in ref_paths:
        content.append({"type": "image", "source": {
            "type": "base64", "media_type": _mime_of(p),
            "data": base64.b64encode(p.read_bytes()).decode()}})
    # PROMPT CACHING. INTENT.md claims caching is "engaged by keeping the
    # screenplay as the stable prompt prefix" — true for OpenAI and Gemini,
    # whose caching is automatic, and false here until now (adversarial
    # review F17). Anthropic's is opt-in per block: without a breakpoint
    # nothing is cached and every pass bills the whole screenplay at full
    # input rate. The reference draft is ~131 KB, roughly 33k tokens, and
    # it is re-sent on every scene scan, breakdown draft, re-draft and
    # bible draft.
    #
    # The ordering was already right — screenplay first, instructions last
    # — so one field turns the existing structure into a cache hit. The
    # breakpoint goes on the LAST stable block, which is the screenplay
    # plus any reference images: everything up to and including it is
    # cached, and the instructions after it vary per call.
    if content:
        content[-1].setdefault("cache_control", {"type": "ephemeral"})
    content.append({"type": "text", "text": instructions})
    out = http(f"{ANTHROPIC_API}/messages", method="POST", headers={
        "x-api-key": key, "anthropic-version": "2023-06-01",
        "content-type": "application/json"}, body={
        "model": model, "max_tokens": MAX_OUTPUT_TOKENS,
        "messages": [{"role": "user", "content": content}]}, timeout=600)
    text = "".join(b.get("text", "") for b in out.get("content", [])
                   if b.get("type") == "text").strip()
    if not text:
        # A cut-off reply is the expensive failure, and it used to surface
        # as a JSON parser message (F11/F20). Name it, and name the cost of
        # the retry, because a retry re-sends the whole screenplay.
        if str(out.get("stop_reason", "")) == "max_tokens":
            raise NarrativeError(
                f"Anthropic/{model} hit its {MAX_OUTPUT_TOKENS}-token output "
                "limit before finishing. The reply is unusable and a re-run "
                "re-sends the whole screenplay — raise the limit rather than "
                "retrying into the same ceiling.")
        raise NarrativeError(f"Anthropic/{model} returned no text.")
    if str(out.get("stop_reason", "")) == "max_tokens":
        raise NarrativeError(
            f"Anthropic/{model} was cut off at its {MAX_OUTPUT_TOKENS}-token "
            "output limit, so the JSON is incomplete. A re-run re-sends the "
            "whole screenplay — raise the limit instead.")
    return text, model


def anthropic_test(http=None) -> str:
    """Cheap connectivity check for Test & save: the models list costs
    nothing and proves the key. Returns the first model id."""
    key = anthropic_key()
    if not key:
        raise NarrativeError("no Anthropic key saved")
    http = http or _http_json
    out = http(f"{ANTHROPIC_API}/models", headers={
        "x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=60)
    models = out.get("data") or []
    if not models:
        raise NarrativeError("Anthropic accepted the key but listed no models")
    return str(models[0].get("id", "ok"))


# ------------------------------------------------ openrouter (chat, text)

def openrouter_complete(doc: bytes, mime: str, instructions: str,
                        ref_paths: tuple = (), http=None) -> tuple[str, str]:
    key = openrouter_key()
    if not key:
        raise NarrativeError("OpenRouter is not connected — connect it in "
                             "Settings → AI & engines")
    http = http or connectors._http_json
    model = OPENROUTER_NARRATIVE_MODEL
    if mime == "application/pdf":
        # Image-only screenplay scans have no extracted text to send.
        raise NarrativeError(
            "this screenplay yielded no extractable text (image-only PDF) — "
            "the OpenRouter narrative path needs text; use OpenAI, Gemini or "
            "Anthropic for this file")
    parts: list = [{"type": "text",
                    "text": "SCREENPLAY FOLLOWS\n==================\n"
                            + doc.decode("utf-8", "replace")}]
    for p in ref_paths:
        parts.append({"type": "image_url", "image_url": {
            "url": f"data:{_mime_of(p)};base64,"
                   + base64.b64encode(p.read_bytes()).decode()}})
    parts.append({"type": "text", "text": instructions})
    out = http(f"{connectors.OPENROUTER_API}/chat/completions", method="POST",
               headers=connectors._or_headers(key), timeout=600, body={
                   "model": model,
                   "messages": [{"role": "user", "content": parts}]})
    msg = ((out.get("choices") or [{}])[0].get("message") or {})
    text = (msg.get("content") or "").strip() if isinstance(msg.get("content"), str) \
        else "".join(p.get("text", "") for p in (msg.get("content") or [])
                     if isinstance(p, dict)).strip()
    if not text:
        detail = (out.get("error") or {}).get("message") or "no text returned"
        raise NarrativeError(f"OpenRouter/{model}: {str(detail)[:300]}")
    return text, f"{model} via OpenRouter"


def complete(provider: str, doc: bytes, mime: str, instructions: str,
             ref_paths: tuple = (), http=None) -> tuple[str, str]:
    if provider == "anthropic":
        return anthropic_complete(doc, mime, instructions, ref_paths, http)
    if provider == "openrouter":
        return openrouter_complete(doc, mime, instructions, ref_paths, http)
    raise NarrativeError(f"unknown narrative provider: {provider}")
