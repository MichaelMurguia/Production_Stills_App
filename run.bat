@echo off
cd /d "%~dp0"
title Screenboard Studio
echo Starting Screenboard Studio...
echo.

REM Dependencies install only when something is actually missing, instead of
REM on every launch. Re-running pip each start meant a network fetch from a
REM batch script every time you opened a local app: slow, offline-hostile,
REM and one of the behaviours antivirus heuristics score against an
REM unsigned script (user report 2026-08-23 — repeated Windows security
REM warnings). The import probe self-heals on upgrade: a release that adds
REM a dependency fails the probe once and installs it.
python -c "import fastapi, uvicorn, multipart, PIL, google.genai, openai, pypdf, cryptography" >nul 2>&1
if errorlevel 1 (
  echo Installing dependencies ^(first run, and after an upgrade^)...
  python -m pip install -q -r requirements.txt
  if errorlevel 1 (
    echo.
    echo Dependency install failed. Screenboard Studio needs Python 3.10 or
    echo newer, and an internet connection for this first step only.
    echo.
    pause
    exit /b 1
  )
)

python -m app
pause
