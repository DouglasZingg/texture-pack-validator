@echo off
setlocal ENABLEDELAYEDEXPANSION

REM Texture Pack Validator - Setup (Windows CMD)

cd /d "%~dp0"

if not exist ".venv" (
  echo Creating virtual environment in .venv ...
  py -3 -m venv .venv
)

echo Activating venv ...
call ".venv\Scripts\activate.bat"

echo Upgrading pip ...
python -m pip install --upgrade pip

echo Installing runtime dependencies ...
pip install -r requirements.txt

echo.
choice /m "Install dev dependencies (pytest) and run tests"
if errorlevel 2 goto done

echo Installing dev dependencies ...
pip install -r requirements-dev.txt

echo Running tests ...
pytest -q

:done
echo.
echo Setup complete.
echo To run the app:  python main.py
endlocal
