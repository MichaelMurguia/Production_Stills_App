#!/usr/bin/env python
"""Local polish loop — boot the app against a throwaway home, auto-reloading.

    .\dev.bat              find an install, copy it in, boot, open a browser
    .\dev.bat --restore    import the newest backup zip from Downloads
    .\dev.bat --keys       let the real API keys through (renders spend)
    .\dev.bat --fresh      wipe the local copy and start over

PowerShell will not run `dev.bat` from the current directory — it needs
the `.\` prefix, which is a Windows thing and not a mistake on your part.
Double-clicking it in Explorer works as well.

Why this exists (user 2026-08-16): "we should iterate locally for a bunch
of these polish items so its fast". A UI change was costing a version
bump, a commit, a zip, a push and a three-minute fleet deploy before it
could be looked at. There is no build step in this app — editing
app/static/* and hard-refreshing is the whole loop, and uvicorn --reload
covers the Python.

Three things it refuses to do by default, each for a reason:

- **It never touches your real install.** SCREENBOARD_HOME points at
  .devhome/ (gitignored). Polishing must not be able to damage the work
  you are polishing FOR.
- **It blanks the API keys.** A dev loop that can spend money on a
  mis-click is not a dev loop. --keys opts back in when you genuinely
  need to render.
- **It refuses a port that is already listening**, rather than serving you
  a stale build from a leaked server — which has happened, and you
  "verify" the wrong thing for twenty minutes before noticing.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / ".devhome"


def port_is_taken(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def free_port(start: int) -> int:
    """Walk up to a port nothing is listening on. Refusing was the old
    behaviour and it was right about the danger — a leaked server serves a
    stale build and you "verify" the wrong thing — but moving to a fresh
    port avoids the same danger without making the user do anything."""
    for p in range(start, start + 40):
        if not port_is_taken(p):
            return p
    return start


def find_install() -> Path | None:
    """Look for an installed Screenboard so `dev.bat` with no arguments
    lands on real content (user 2026-08-16: "make the local loop EASY —
    batch file and we are in local mode"). An install is a folder holding
    both run.bat and app/main.py; anything else is a coincidence."""
    home = Path.home()
    roots = [home / "Downloads", home / "Desktop", home / "Documents",
             Path("C:/"), home]
    seen = set()
    for root in roots:
        if not root.exists() or root in seen:
            continue
        seen.add(root)
        try:
            entries = list(root.iterdir())
        except OSError:
            continue
        for d in entries:
            try:
                if (d.is_dir() and d.resolve() != ROOT
                        and (d / "run.bat").exists()
                        and (d / "app" / "main.py").exists()):
                    return d
            except OSError:
                continue
    return None


def newest_download() -> Path | None:
    """The backup you just downloaded. Naming it should not be homework."""
    d = Path.home() / "Downloads"
    zips = sorted((p for p in d.glob("*.zip") if p.is_file()),
                  key=lambda p: p.stat().st_mtime, reverse=True) if d.exists() else []
    return zips[0] if zips else None


def restore(zip_path: Path) -> None:
    """Import a backup through the app's OWN restore, not a bare
    extractall: it validates every member against traversal, reads the
    project's real name out of the archive, avoids colliding with an
    existing slug, and stages into a hidden directory renamed into place
    so a half-written tree never appears on the shelf. Rewriting any of
    that here would be a worse copy of it.

    SCREENBOARD_HOME is already set, so `app.paths` resolves to .devhome
    the moment it is imported. The repo root goes on sys.path first —
    this script lives in scripts/, so `app` is not importable from here
    by default."""
    sys.path.insert(0, str(ROOT))
    from app import backup
    r = backup.restore_backup(zip_path.read_bytes())
    (HOME / "active_project.json").write_text(
        json.dumps({"slug": r["slug"]}), encoding="utf-8")
    print(f"restored \"{r['name']}\" from {zip_path.name} "
          f"-> .devhome/projects/{r['slug']}/  (opened by default)")


def clone_install(src: Path) -> None:
    """Copy an installed app's content into .devhome — ONCE, and only what
    is missing. The repo supplies the code; the install supplies real
    productions to polish against. Nothing is ever written back: the whole
    point of a dev loop is that it cannot damage the work it exists to
    improve."""
    import shutil
    copied = []
    for name in ("projects", "data", "project_state"):
        s_dir = src / name
        d_dir = HOME / name
        if s_dir.exists() and not d_dir.exists():
            shutil.copytree(s_dir, d_dir)
            copied.append(name)
    for name in ("settings.json", "active_project.json", "app_state.json"):
        s_f, d_f = src / name, HOME / name
        if s_f.exists() and not d_f.exists():
            shutil.copyfile(s_f, d_f)
            copied.append(name)
    print(f"cloned from {src}: {', '.join(copied) or 'nothing new'}"
          f"  (delete .devhome or pass --fresh to re-copy)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-open", action="store_true",
                    help="do not open a browser")
    ap.add_argument("--restore", metavar="ZIP", nargs="?", const="newest",
                    help="a backup zip from Productions -> Back up; with no "
                         "path, the newest zip in your Downloads")
    ap.add_argument("--from-install", metavar="DIR",
                    help="copy productions out of an installed Screenboard "
                         "(the folder holding run.bat) — real content, "
                         "copied once, never written back")
    ap.add_argument("--keys", action="store_true",
                    help="pass the real API keys through (renders cost money)")
    ap.add_argument("--fresh", action="store_true",
                    help="delete .devhome first")
    a = ap.parse_args()
    a.port_given = any(x.startswith("--port") for x in sys.argv[1:])

    if a.fresh and HOME.exists():
        import shutil
        shutil.rmtree(HOME, ignore_errors=True)
        print("cleared .devhome/")
    HOME.mkdir(parents=True, exist_ok=True)

    # No flags at all: find an install, clone it once, and go. The point
    # of a polish loop is that starting it costs nothing.
    if not a.from_install and not a.restore and not (HOME / "projects").exists():
        found = find_install()
        if found:
            print(f"found an install at {found}")
            clone_install(found)
        else:
            print("no installed Screenboard found — starting empty "
                  "(pass --from-install DIR if it lives somewhere unusual)")

    if a.from_install:
        src = Path(a.from_install)
        if not (src / "app").exists():
            print(f"{src} does not look like an install (no app/ inside)",
                  file=sys.stderr)
            return 2
        clone_install(src)

    if a.restore:
        z = newest_download() if a.restore == "newest" else Path(a.restore)
        if z is None:
            print("no zip found in Downloads — pass the path: "
                  r'dev.bat --restore "C:\\path\\to\\backup.zip"',
                  file=sys.stderr)
            return 2
        if not z.exists():
            print(f"no such zip: {z}", file=sys.stderr)
            return 2
        os.environ["SCREENBOARD_HOME"] = str(HOME)
        try:
            restore(z)
        except Exception as e:  # noqa: BLE001 — a bad zip is a message, not a stack
            print(f"could not restore {z.name}: {e}", file=sys.stderr)
            return 2

    port = a.port if a.port_given else free_port(a.port)
    if a.port_given and port_is_taken(port):
        print(f"port {port} is already listening — stop that server or drop "
              f"--port and one will be chosen.", file=sys.stderr)
        return 1
    if port != a.port:
        print(f"port {a.port} was busy — using {port}")

    env = dict(os.environ)
    env["SCREENBOARD_HOME"] = str(HOME)
    if not a.keys:
        for k in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY",
                  "OPENROUTER_API_KEY", "REPLICATE_API_TOKEN"):
            env[k] = ""

    url = f"http://127.0.0.1:{port}"
    if not a.no_open:
        import threading
        import webbrowser
        threading.Timer(2.0, lambda: webbrowser.open(url)).start()
    print("")
    print(f"  {url}")
    print("")
    print("  home    .devhome/")
    print(f"  keys    {'LIVE — renders will spend' if a.keys else 'blanked'}")
    print("  reload  app/**.py automatically; app/static/* on a hard refresh"
          " (Ctrl-Shift-R)\n")
    return subprocess.call(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--port", str(port), "--reload", "--reload-dir", str(ROOT / "app")],
        cwd=ROOT, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
