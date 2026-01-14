@echo off
title taskscheduler - run
cd /d "%~dp0"
uv run python main.py %* --log-level INFO --detailed-logs false
