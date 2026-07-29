"""Activity log — the app's flight recorder.

Every mutating API call (generations, approvals, rejections with their
reasons, deletions, errors) is appended to data/activity_log.jsonl so a
debrief can reconstruct what the user did, what failed, and why — without
copy/paste. Secrets are redacted before anything is written.
"""
from __future__ import annotations

import datetime as dt
import json
from typing import Any

from . import paths

LOG = paths.DATA / "activity_log.jsonl"

_REDACT_MARKERS = ("key", "token", "secret", "file_data", "image_url", "b64")
_MAX_STR = 400


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: ("[redacted]" if any(m in k.lower() for m in _REDACT_MARKERS)
                    else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value[:20]]
    if isinstance(value, str) and len(value) > _MAX_STR:
        return value[:_MAX_STR] + f"… [{len(value)} chars]"
    return value


def log(event: dict) -> None:
    try:
        paths.ensure_dirs()
        event = {"ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                 **_redact(event)}
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass  # the flight recorder must never take the plane down
