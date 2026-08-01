@echo off
title taskscheduler - run by name %~1
cd /d "%~dp0"
if "%~1"=="" (
    uv run python main.py --run-name
) else (
    uv run python main.py --run-name "%~1"
)
pause
