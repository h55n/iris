@echo off
REM Starts Iris on this PC, then opens it. Install it as an app from the browser menu (Install Iris).
cd /d "%~dp0"
start "" http://127.0.0.1:8473
python iris\webui.py --store store
