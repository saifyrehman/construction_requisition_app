@echo off
echo ========================================
echo   🏗️ Construction Requisition System
echo   Conda Environment Setup
echo ========================================
echo.

echo Step 1: Creating conda environment...
conda create -n requisition_system python=3.10 -y

if errorlevel 1 (
    echo ❌ Failed to create conda environment
    pause
    exit /b 1
)

echo.
echo Step 2: Activating environment...
call conda activate requisition_system

echo.
echo Step 3: Installing packages...
pip install streamlit streamlit-option-menu streamlit-aggrid pandas plotly bcrypt fuzzywuzzy python-Levenshtein reportlab openpyxl jinja2 python-dotenv pydantic pyjwt Pillow sqlalchemy

echo.
echo Step 4: Creating directories...
mkdir pages 2>nul
mkdir static 2>nul
mkdir templates 2>nul
mkdir utils 2>nul

echo.
echo Step 5: Creating __init__.py files...
echo # Pages package > pages\__init__.py
echo # Utils package > utils\__init__.py

echo.
echo ========================================
echo   ✅ Setup Complete!
echo ========================================
echo.
echo To run the application:
echo   1. conda activate requisition_system
echo   2. streamlit run app.py
echo.
echo Default Login:
echo   Username: admin
echo   Password: admin123
echo.
pause