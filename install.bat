@echo off
python -m venv venv
call venv\Scripts\activate
python -m pip install -r requirements.txt
echo Installation complete!
