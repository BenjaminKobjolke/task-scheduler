@echo off
echo Installing Telegram Bot dependency...
cd /d "%~dp0.."
uv sync --extra bot
uv add --editable "D:\GIT\BenjaminKobjolke\telegram-bot"
echo Done.
pause
