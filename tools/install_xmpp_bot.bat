@echo off
echo Installing XMPP Bot dependency...
cd /d "%~dp0.."
uv sync --extra xmpp
echo Done.
pause
