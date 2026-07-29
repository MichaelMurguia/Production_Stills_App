@echo off
cd /d "%~dp0"
echo Starting Beltminer Production Stills...
python -m pip install -q -r requirements.txt
python -m app
pause
