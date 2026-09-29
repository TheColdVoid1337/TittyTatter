@echo off
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo Creating Windows virtual environment...
  py -m venv .venv || python -m venv .venv
  if errorlevel 1 goto :error
)

.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :error

.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if errorlevel 1 goto :error

.venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed --name TittyTatter --add-data "VERSION;." app.py
if errorlevel 1 goto :error

echo Build complete.
exit /b 0

:error
echo Build failed.
pause
exit /b 1
