@echo off
REM Setup script for Gemini Web Chat Automation Pipeline

echo Setting up Gemini Web Chat Automation Pipeline...

REM Create virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Install Playwright browsers
echo Installing Playwright browsers...
python -m playwright install chromium

echo.
echo Setup complete! You can now run the pipeline using:
echo   run_pipeline.bat --prompt "Your question here"
echo   run_pipeline.bat --prompt-file prompts.txt
echo.
echo To see all options, run:
echo   run_pipeline.bat --help