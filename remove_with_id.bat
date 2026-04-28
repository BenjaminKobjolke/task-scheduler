@echo off
cd /d "%~dp0"
uv run python main.py --delete %1
