@echo off
cd /d "%~dp0"
uv run pyinstaller --name TaskScheduler --onefile main.py
