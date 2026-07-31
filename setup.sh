#!/bin/bash

# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# Force reinstall streamlit-option-menu
pip install --no-cache-dir streamlit-option-menu

# Create necessary directories
mkdir -p static
mkdir -p temp

echo "✅ Setup completed successfully!"
