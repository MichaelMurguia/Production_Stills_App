@echo off
REM Local mode. Just run this — no arguments needed.
REM It finds your installed Screenboard, copies its productions in once
REM (never writing back), picks a free port and opens the browser.
REM   dev.bat --keys    let the real API keys through (renders spend money)
REM   dev.bat --fresh   wipe the local copy and start over
cd /d "%~dp0"
python scripts\dev.py %*
