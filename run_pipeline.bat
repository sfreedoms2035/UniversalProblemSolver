@echo off
REM Gemini Web Chat Automation Pipeline Runner
REM Usage: run_pipeline.bat [options]

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.7 or higher
    exit /b 1
)

REM Check if this is the first run
if not exist "venv" (
    echo First time setup - creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    echo Installing Playwright browsers...
    python -m playwright install chromium
) else (
    call venv\Scripts\activate.bat
)

REM Run the pipeline with provided arguments
python main.py %*
