@echo off
title taskscheduler - shutdown
cd /d "%~dp0"
uv run python main.py --shutdown
