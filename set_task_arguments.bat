@echo off
title taskscheduler - set arguments for task %1
cd /d "%~dp0"
uv run python main.py --set-arguments %1
