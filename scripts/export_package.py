"""Source zip of the CURRENT TREE — a developer convenience, not the
product. `scripts/stage_release.py` builds what customers download.

Audited 2026-08-23. This walked `root.rglob('*')` and excluded only
__pycache__, so on any machine where the app had actually been run it
zipped `settings.json` — the user's plaintext API keys — plus
`.claude/settings.local.json` (which CLAUDE.md says must never ship),
1716 files of `data/`, and `project_state/`. Nobody had shipped one, but
the script was a loaded gun pointed at exactly the boundary the project
states as hard: nothing from data/ or project_state/ is ever packaged.

Git is the authority on what is shareable, so the exclusion is not a
hand-maintained list that drifts: anything ignored or untracked is out.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Belt and braces. `git ls-files` already excludes these, but a name that
# reaches the zip here is a credential in someone's inbox — so it is
# checked again against the final member list, and a hit is fatal.
FORBIDDEN = ("settings.json", "settings.local.json", ".env", "data/",
             "project_state/", "projects/", ".devhome/")


def tracked_files() -> list[str]:
    """Committed and staged files only. Untracked and ignored paths — every
    place a secret actually lives — cannot appear."""
    out = subprocess.run(["git", "ls-files", "--cached", "--exclude-standard"],
                         cwd=ROOT, check=True, capture_output=True, text=True)
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def offenders(members: list[str]) -> list[str]:
    return sorted({m for m in members
                   for f in FORBIDDEN
                   if (m.endswith(f) if not f.endswith("/") else f in m + "/")})


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(ROOT.parent / (ROOT.name + "_source.zip")))
    a = ap.parse_args()
    out = Path(a.output)

    members = tracked_files()
    bad = offenders(members)
    if bad:
        print("REFUSING TO PACKAGE — these would carry secrets or user work:",
              file=sys.stderr)
        for b in bad:
            print("  " + b, file=sys.stderr)
        return 2

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in members:
            src = ROOT / rel
            if src.is_file():
                z.write(src, str(Path(ROOT.name) / rel))
    print(f"{out}  ({len(members)} files, tracked only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
