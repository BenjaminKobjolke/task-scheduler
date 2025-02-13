@echo off
cd /d D:\GIT\BenjaminKobjolke\task-scheduler
call venv\Scripts\activate.bat
python main.py %* --log-level INFO --detailed-logs false
