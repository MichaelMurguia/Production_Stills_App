#!/usr/bin/env python
"""Watch the cloud-studio fleet roll a release out, and say when it is live.

A tenant update (scripts/update_tenants.sh) only TRIGGERS the Railway
rebuild and returns immediately; the studios keep serving the old build
until each new image finishes and swaps in (~minutes, with a graceful
drain). Standard practice after a release: run this as a listener — it
discovers the ACTIVE studios, polls each studio's build status AND its
/api/healthz, and exits when every studio serves the target commit (or a
build fails). Meant to be launched in the background so it reports back on
its own.

  python scripts/watch_tenants.py               # target = current git HEAD
  python scripts/watch_tenants.py <commit>      # explicit target commit
  python scripts/watch_tenants.py --once        # one pass, print, exit

Exit: 0 all live · 2 a build FAILED/CRASHED · 1 timeout. The admin token is
read from $ADMIN_EXPORT_TOKEN or ~/.screenboard_admin_token (never printed),
same as update_tenants.sh.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("SCREENBOARD_BASE_URL", "https://www.screenboardstudio.com")
TENANT_BASE = os.environ.get("SCREENBOARD_TENANT_BASE", "screenboardstudio.com")
TOKEN_FILE = os.environ.get("SCREENBOARD_ADMIN_TOKEN_FILE",
                            str(Path.home() / ".screenboard_admin_token"))
POLL_SECONDS = int(os.environ.get("WATCH_POLL_SECONDS", "20"))
TIMEOUT_SECONDS = int(os.environ.get("WATCH_TIMEOUT_SECONDS", "1200"))
DEAD = {"FAILED", "CRASHED"}


def _token() -> str:
    t = os.environ.get("ADMIN_EXPORT_TOKEN", "").strip()
    if not t and os.path.exists(TOKEN_FILE):
        t = Path(TOKEN_FILE).read_text(encoding="utf-8").strip()
    if not t:
        sys.exit(f"error: no admin token (set $ADMIN_EXPORT_TOKEN or write {TOKEN_FILE})")
    return t


def _get(url: str, token: str | None = None, timeout: int = 20) -> tuple[int, str]:
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # network blip — treat as retryable
        return 0, str(e)


def _target() -> str:
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        return sys.argv[1].strip()[:12]
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
                         capture_output=True, text=True).stdout.strip()
    return sha[:12]


def _deploy_status(studio_deploys: list, target: str) -> str:
    """Railway status of this studio's deploy for the target commit, '' if none yet."""
    for d in studio_deploys:
        if (d.get("meta", {}).get("commitHash", "")[:12]) == target:
            return d.get("status", "")
    return ""


def snapshot(token: str, target: str) -> tuple[dict, bool, str | None]:
    """(per-studio state, all_live, dead_studio_or_None)."""
    code, body = _get(f"{BASE_URL}/admin/tenants/update?status=1", token)
    if code != 200:
        return {"_error": f"status probe HTTP {code}"}, False, None
    fleet = json.loads(body)
    state, all_live, dead = {}, True, None
    for studio, deploys in fleet.items():
        if isinstance(deploys, str):
            state[studio] = {"deploy": f"ERR {deploys}", "rev": "?", "live": False}
            all_live = False
            continue
        dstatus = _deploy_status(deploys, target)
        hc, hbody = _get(f"https://{studio}.{TENANT_BASE}/api/healthz", timeout=10)
        rev = ver = "?"
        if hc == 200:
            try:
                j = json.loads(hbody); rev = j.get("rev", "?"); ver = j.get("version", "?")
            except Exception:
                pass
        live = rev[:12] == target
        state[studio] = {"deploy": dstatus or "(none)", "rev": rev, "version": ver, "live": live}
        if not live:
            all_live = False
        if dstatus in DEAD and not live:
            dead = studio
    return state, all_live, dead


def _line(state: dict) -> str:
    if "_error" in state:
        return state["_error"]
    return " · ".join(f"{s}: {v['deploy']}/{v['rev'][:12]}"
                      + (" LIVE" if v["live"] else "") for s, v in state.items())


def main() -> int:
    once = "--once" in sys.argv
    token, target = _token(), _target()
    print(f"watching fleet for {target} (timeout {TIMEOUT_SECONDS}s, every {POLL_SECONDS}s)")
    start = time.time()
    while True:
        state, all_live, dead = snapshot(token, target)
        elapsed = int(time.time() - start)
        print(f"[{elapsed:4}s] {_line(state)}", flush=True)
        if once:
            return 0 if all_live else 1
        if all_live:
            print(f"ALL LIVE at {target}")
            return 0
        if dead:
            print(f"BUILD FAILED: {dead} — check its workspace row 'detail'; update_tenants retries next run")
            return 2
        if elapsed >= TIMEOUT_SECONDS:
            print(f"TIMEOUT after {elapsed}s — not all studios serving {target}")
            return 1
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
