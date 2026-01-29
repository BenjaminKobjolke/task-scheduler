@echo off
d:
cd "D:\GIT\BenjaminKobjolke\cli-code-analyzer"

call venv\Scripts\python.exe main.py --language python --path "D:\GIT\BenjaminKobjolke\task-scheduler" --verbosity minimal --output "D:\GIT\BenjaminKobjolke\task-scheduler\code_analysis_results" --maxamountoferrors 50 --rules "D:\GIT\BenjaminKobjolke\task-scheduler\code_analysis_rules.json"

cd %~dp0..
