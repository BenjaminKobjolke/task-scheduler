@echo off
title taskscheduler - set start time for task %1 to %2
cd /d "%~dp0"
uv run python main.py --set-start-time %1 %2
