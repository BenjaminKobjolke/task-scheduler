@echo off
echo Reinstalling all dependencies (clean)...
cd /d "%~dp0.."
if exist .venv rmdir /s /q .venv
uv sync --all-extras
if errorlevel 1 goto :failed
echo Done.
if not defined TICKETS_WATCHER_COMMAND_RUN pause
exit /b 0

:failed
set "result=%errorlevel%"
echo Reinstall failed with exit code %result%.
if not defined TICKETS_WATCHER_COMMAND_RUN pause
exit /b %result%
