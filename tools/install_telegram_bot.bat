@echo off
echo Installing Telegram Bot dependency...
cd /d "%~dp0.."
uv sync --extra bot
if errorlevel 1 goto :failed
uv add --editable "D:\GIT\BenjaminKobjolke\telegram-bot"
if errorlevel 1 goto :failed
echo Done.
if not defined TICKETS_WATCHER_COMMAND_RUN pause
exit /b 0

:failed
set "result=%errorlevel%"
echo Installation failed with exit code %result%.
if not defined TICKETS_WATCHER_COMMAND_RUN pause
exit /b %result%
