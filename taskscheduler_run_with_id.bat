@echo off
title taskscheduler - run with id %1
cd /d "%~dp0"
call venv\Scripts\activate.bat
python main.py --run_id %1
