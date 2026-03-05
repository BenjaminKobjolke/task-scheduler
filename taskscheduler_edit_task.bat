@echo off
title taskscheduler - edit task %1
cd /d "%~dp0"
uv run python main.py --edit %1
