@echo off
title taskscheduler - rename task %1
cd /d "%~dp0"
uv run python main.py --rename %1
