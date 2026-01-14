@echo off
cd /d "%~dp0"
uv run python main.py --add --log-level INFO --detailed-logs false
