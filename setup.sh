#!/usr/bin/env bash
set -e

# Texture Pack Validator - Setup (macOS/Linux)

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment in .venv ..."
  python3 -m venv .venv
fi

echo "Activating venv ..."
source .venv/bin/activate

echo "Upgrading pip ..."
python -m pip install --upgrade pip

echo "Installing runtime dependencies ..."
pip install -r requirements.txt

read -r -p "Install dev dependencies (pytest) and run tests? [y/N] " ans
if [[ "$ans" =~ ^[Yy]$ ]]; then
  pip install -r requirements-dev.txt
  pytest -q
fi

echo "Setup complete."
echo "To run the app:  python main.py"
