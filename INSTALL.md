# Installation

## Requirements

- Python 3.10 or newer
- No third-party Python packages are required beyond `requirements.txt`

## Windows — do this first (it saves a scary dialog)

Windows tags **every file inside a downloaded ZIP** with a "came from the
internet" mark. Run `run.bat` from a ZIP you extracted normally and Windows
shows:

> **The publisher could not be verified. Are you sure you want to run this
> software?** … Unknown Publisher

Nothing is wrong with the download — that dialog appears for every
unsigned script from the internet, including this one. Clear it once, at
the ZIP, before extracting:

1. **Right-click `screenboard-studio-<version>.zip` → Properties.**
2. At the bottom of the General tab, tick **Unblock**, then **OK**.
3. *Then* extract the ZIP and run `run.bat`.

Extracted already? Either re-do the three steps on the ZIP and extract
again, or clear the mark on the extracted folder in PowerShell:

```powershell
Get-ChildItem -Recurse "C:\path\to\ScreenboardStudio" | Unblock-File
```

If you see the dialog anyway, **Run** is safe — you can read every line of
`run.bat` and the Python source in the folder first. (We do not yet
code-sign the launcher; a signed release is planned.)

## Running the app

From the package root:

```
run.bat            (Windows)
python -m app      (macOS / Linux, or any platform)
```

Then open <http://127.0.0.1:8000>. The app runs entirely on your machine;
it reaches the network only to call the AI engines whose keys you enter in
**Settings → AI & engines**.

**Seeing an old version of a screen after updating?** Hard-refresh the
browser tab (Ctrl+F5). Released builds stamp their assets per version, so
this only bites a tab left open across an upgrade.

## Local tools

```bash
python scripts/validate_spec.py examples/minimal_valid_spec.json
python scripts/compile_prompt.py examples/minimal_valid_spec.json
python scripts/audit_spec.py examples/minimal_valid_spec.json
python scripts/state_manager.py show
python -m unittest discover -s tests -v
```
