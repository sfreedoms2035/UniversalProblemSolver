#!/usr/bin/env python3
"""
Basic test script to verify the pipeline can be imported and initialized.
"""

import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from gemini_pipeline import GeminiPipeline, parse_arguments
    print("[OK] Successfully imported GeminiPipeline")
    
    # Test pipeline initialization
    pipeline = GeminiPipeline(headless=True, output_dir="./test_output")
    print("[OK] Pipeline initialized successfully")
    
    # Test argument parsing
    sys.argv = ['test', '--prompt', 'test prompt']
    args = parse_arguments()
    print(f"[OK] Arguments parsed successfully: prompt='{args.prompt}'")
    
    # Clean up test directory
    import shutil
    test_dir = Path("./test_output")
    if test_dir.exists():
        shutil.rmtree(test_dir)
    
    print("\n[OK] All basic tests passed!")
    
except ImportError as e:
    print(f"[ERROR] Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    sys.exit(1)