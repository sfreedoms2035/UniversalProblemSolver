# Quick Start Guide

## Prerequisites
- Python 3.7 or higher
- Windows (batch scripts) or Linux/Mac (adjust commands accordingly)

## Installation

### Option 1: Automatic Setup (Windows)
```batch
setup.bat
```

### Option 2: Manual Setup
```batch
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium
```

## Basic Usage

### Simplest Test (No Browser Required)
```batch
python test_pipeline_simple.py
```

### Your First Real Pipeline Run
```batch
# Using direct prompt
run_pipeline.bat --prompt "What is artificial intelligence?"

# Using prompt from file
echo Explain machine learning in simple terms > prompt.txt
run_pipeline.bat --prompt-file prompt.txt
```

### See the Browser in Action
```batch
run_pipeline.bat --prompt "Hello, how are you?" --visible
```

## What Gets Created

After running the pipeline:
```
output/
├── response_20240101_120000.txt    # Your prompt and Gemini's response
└── response_20240101_120000.json   # Metadata about the response
```

## Common Commands

```batch
# Basic usage
run_pipeline.bat --prompt "Your question here"

# Save to specific file
run_pipeline.bat --prompt "Your question" --output my_response

# Use custom output directory
run_pipeline.bat --prompt "Your question" --output-dir ./my_results

# Run with visible browser
run_pipeline.bat --prompt "Your question" --visible

# Increase timeout for longer responses
run_pipeline.bat --prompt "Write a long explanation" --timeout 300
```

## Next Steps

1. Check the output directory for results
2. Read `examples.txt` for more advanced usage
3. Read `README.md` for detailed documentation
4. Try different prompts and see the responses

## Need Help?

Run the help command:
```batch
run_pipeline.bat --help
```

Or check the documentation files:
- `README.md` - Full documentation
- `examples.txt` - Usage examples
- `QUICK_START.md` - This file