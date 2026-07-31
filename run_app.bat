@echo off
echo ========================================
echo   🏗️ Construction Requisition System
echo ========================================
echo.
echo Activating environment...
call conda activate requisition_system

if errorlevel 1 (
    echo ❌ Failed to activate conda environment
    echo Please run setup_conda.bat first
    pause
    exit /b 1
)

echo.
echo Starting application...
streamlit run app.py

pause