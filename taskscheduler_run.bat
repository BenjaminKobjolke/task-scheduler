@echo off
title taskscheduler - run
cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py %* --log-level INFO --detailed-logs false
