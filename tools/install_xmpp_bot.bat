@echo off
echo Installing XMPP Bot dependency...

where rustc >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Rust compiler not found.
    echo The XMPP dependency requires Rust to compile on Windows.
    echo Please install Rust from https://rustup.rs/ and restart your terminal.
    pause
    exit /b 1
)

cd /d "%~dp0.."
uv sync --extra xmpp
echo Done.
pause
