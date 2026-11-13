@echo off
cd /d "%~dp0.."
set "PROJECT_ROOT=%CD%"
if not defined CLI_CODE_ANALYZER_ROOT set "CLI_CODE_ANALYZER_ROOT=%PROJECT_ROOT%\..\cli-code-analyzer"
set "ANALYZER_ROOT=%CLI_CODE_ANALYZER_ROOT%"
if not exist "%ANALYZER_ROOT%\venv\Scripts\python.exe" (
    echo ERROR: Analyzer Python not found at "%ANALYZER_ROOT%\venv\Scripts\python.exe".
    echo Set CLI_CODE_ANALYZER_ROOT to the cli-code-analyzer checkout.
    exit /b 1
)
cd /d "%ANALYZER_ROOT%"

call venv\Scripts\python.exe ruff_fixer.py --path "%PROJECT_ROOT%" --rules "%PROJECT_ROOT%\code_analysis_rules.json" --dry-run
set "result=%errorlevel%"

cd /d "%~dp0.."
exit /b %result%
