@echo off
echo Installing Telegram Bot dependency...
cd /d "%~dp0.."
uv add --editable "D:\GIT\BenjaminKobjolke\telegram-bot"
echo Done.
pause
