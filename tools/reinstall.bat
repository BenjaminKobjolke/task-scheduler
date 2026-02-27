@echo off
echo Reinstalling all dependencies (clean)...
cd /d "%~dp0.."
if exist .venv rmdir /s /q .venv
uv sync --all-extras
echo Done.
pause
