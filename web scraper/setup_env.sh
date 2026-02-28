#!/bin/bash
echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing required packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Installation complete."
echo "To activate later, run: source venv/bin/activate"