@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe call run.bat
call .venv\Scripts\activate.bat
pip install -r requirements-dev.txt
pyinstaller --noconfirm --clean --windowed --name TittyTatter --add-data "VERSION;." app.py
pause
