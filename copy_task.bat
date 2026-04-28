@echo off
title taskscheduler - copy task %1
cd /d "%~dp0"
uv run python main.py --copy-task %1
