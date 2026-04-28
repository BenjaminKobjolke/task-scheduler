@echo off
title taskscheduler - run with id %1
cd /d "%~dp0"
uv run python main.py --run_id %1
