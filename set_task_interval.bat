@echo off
title taskscheduler - set interval for task %1 to %2 minutes
cd /d "%~dp0"
uv run python main.py --set-interval %1 %2
