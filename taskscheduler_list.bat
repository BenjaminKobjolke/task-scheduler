@echo off
cd /d "%~dp0"
if "%~1"=="" (
    uv run python main.py --list
) else (
    uv run python main.py --list %1
)
pause
