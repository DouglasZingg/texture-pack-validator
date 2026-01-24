@echo off
setlocal

REM Texture Pack Validator - Run (Windows CMD)
REM - Ensures venv exists (via setup.bat if needed)
REM - Activates venv
REM - Runs the app

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo Virtual environment not found. Running setup.bat ...
  call setup.bat
)

call ".venv\Scripts\activate.bat"
python main.py

endlocal
