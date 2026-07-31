#!/bin/bash

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install each package explicitly
pip install streamlit
pip install streamlit-option-menu==0.1.2
pip install streamlit-aggrid
pip install pandas numpy plotly
pip install bcrypt fuzzywuzzy python-Levenshtein
pip install reportlab openpyxl
pip install jinja2 python-dotenv
pip install pydantic pyjwt Pillow sqlalchemy xlrd
pip install websockets

# Verify installation
python -c "import streamlit_option_menu; print('streamlit-option-menu installed successfully')"

# Create necessary directories
mkdir -p static
mkdir -p temp

echo "✅ Setup completed successfully!"
