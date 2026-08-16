@echo off
REM Local mode. In PowerShell you must prefix it:  .\dev.bat
REM (PowerShell does not run commands from the current directory.)
REM Double-clicking it in Explorer works too.
REM
REM   .\dev.bat                 your installed Screenboard's productions
REM   .\dev.bat --restore       the newest backup zip in your Downloads
REM   .\dev.bat --keys          let the real API keys through (renders spend)
REM   .\dev.bat --fresh         wipe the local copy and start over
cd /d "%~dp0"
python scripts\dev.py %*
