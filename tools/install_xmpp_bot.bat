@echo off
echo Installing XMPP Bot dependency...
cd /d "%~dp0.."
uv add --editable "D:\GIT\BenjaminKobjolke\xmpp-bot"
echo Done.
pause
