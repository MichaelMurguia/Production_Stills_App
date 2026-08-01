#!/usr/bin/env python
"""Stage a release: archive HEAD as the versioned zip and refresh the
canonical latest. Run AFTER committing the VERSION bump — the archive is
of HEAD, not the worktree. Versioned zips are immutable: changing app/
without bumping VERSION turns CI red."""
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ["app", "requirements.txt", "run.bat", "README.md", "INSTALL.md", "VERSION"]

version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
rel = ROOT / "storefront" / "releases"
rel.mkdir(parents=True, exist_ok=True)
target = rel / f"screenboard-studio-{version}.zip"
subprocess.run(["git", "-c", "core.autocrlf=false", "archive",
                "-o", str(target), "HEAD", "--", *INCLUDE],
               cwd=ROOT, check=True)
shutil.copyfile(target, rel / "screenboard-studio.zip")
print(f"staged {target.name} + canonical screenboard-studio.zip")
