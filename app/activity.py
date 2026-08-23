"""Activity log — the app's flight recorder.

Every mutating API call (generations, approvals, rejections with their
reasons, deletions, errors) is appended to data/activity_log.jsonl so a
debrief can reconstruct what the user did, what failed, and why — without
copy/paste. Secrets are redacted before anything is written.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from typing import Any

from . import paths

def _log_path():
    # Computed per call — paths.DATA moves with the active project.
    return paths.DATA / "activity_log.jsonl"


_REDACT_MARKERS = ("key", "token", "secret", "file_data", "image_url", "b64")
_MAX_STR = 400

# Field-name redaction is not enough, and the gap is reachable (audited
# 2026-08-23). A user's own key can arrive as the VALUE of an innocent
# field: the request middleware logs `str(e)[:500]` on a raised route and
# the response body on any 4xx/5xx, both under "error". An upstream that
# echoes the credential in its error message — careless gateways do, and a
# custom engine's base_url is user-supplied, so the endpoint need not be
# ours — puts the key straight into the flight recorder. From there it
# rides a project backup, which we describe to users as shareable creative
# work. Proven end to end before this was written.
#
# So values are scrubbed too, by two passes:
#   1. Every secret this install actually holds, matched literally. No
#      false positives, and it catches any shape a provider invents.
#   2. A shape match for the common prefixed forms, which covers a key
#      being VERIFIED (the Test button) before it is ever stored.
_KEY_SHAPE = re.compile(r"\b(sk|rk|pk|xai|gsk|AIza)[-_A-Za-z0-9]{16,}")


def _configured_secrets() -> tuple[str, ...]:
    """Every credential the install holds right now. Read per call and
    never cached — a key added mid-session must be scrubbed too."""
    try:
        from . import generate
        s = generate.load_settings()
    except Exception:
        return ()
    out = []
    for k, v in s.items():
        if any(m in k.lower() for m in ("key", "token", "secret")) and isinstance(v, str):
            out.append(v)
    for e in s.get("custom_engines", []) or []:
        if isinstance(e, dict) and isinstance(e.get("api_key"), str):
            out.append(e["api_key"])
    # Longest first: a key that contains another as a prefix must not be
    # half-scrubbed and leave a usable tail behind.
    return tuple(sorted({v for v in out if len(v.strip()) >= 8}, key=len, reverse=True))


def _scrub(text: str, secrets: tuple[str, ...]) -> str:
    for sec in secrets:
        if sec in text:
            text = text.replace(sec, "[redacted]")
    return _KEY_SHAPE.sub("[redacted]", text)


def _redact(value: Any, secrets: tuple[str, ...] | None = None) -> Any:
    if secrets is None:
        secrets = _configured_secrets()
    if isinstance(value, dict):
        return {k: ("[redacted]" if any(m in k.lower() for m in _REDACT_MARKERS)
                    else _redact(v, secrets)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v, secrets) for v in value[:20]]
    if isinstance(value, str):
        value = _scrub(value, secrets)
        if len(value) > _MAX_STR:
            return value[:_MAX_STR] + f"… [{len(value)} chars]"
    return value


def log(event: dict) -> None:
    try:
        paths.ensure_dirs()
        event = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 **_redact(event)}
        with _log_path().open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass  # the flight recorder must never take the plane down
