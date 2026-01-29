@echo off
d:
cd "D:\GIT\BenjaminKobjolke\cli-code-analyzer"

call venv\Scripts\python.exe ruff_fixer.py --path "D:\GIT\BenjaminKobjolke\task-scheduler" --rules "D:\GIT\BenjaminKobjolke\task-scheduler\code_analysis_rules.json" --dry-run

cd %~dp0..
