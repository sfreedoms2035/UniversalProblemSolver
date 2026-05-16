#!/usr/bin/env python3
"""
Simple test script to demonstrate the pipeline functionality without actual browser automation.
This simulates the pipeline flow to show how it would work.
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime


class MockGeminiPipeline:
    """Mock version of the pipeline for testing without browser automation"""
    
    def __init__(self, output_dir="./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    async def run(self, prompt=None, prompt_file=None, output_filename=None):
        """Mock pipeline execution"""
        # Get prompt from file or argument
        if prompt_file:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt = f.read().strip()
        elif not prompt:
            raise ValueError("Either prompt or prompt_file must be provided")
            
        print(f"[MOCK] Navigating to Gemini web chat...")
        await asyncio.sleep(0.5)  # Simulate navigation time
        
        print(f"[MOCK] Sending prompt: {prompt[:50]}...")
        await asyncio.sleep(0.5)  # Simulate typing time
        
        print(f"[MOCK] Waiting for response...")
        await asyncio.sleep(1)  # Simulate response time
        
        # Mock response based on prompt
        mock_response = f"""This is a mock response to your prompt:

Prompt: {prompt}

[In a real scenario, this would be Gemini's actual response to your question.

The pipeline would:
1. Open Gemini web chat
2. Type your prompt in the input field
3. Click send button
4. Wait for Gemini to generate a response
5. Extract the response text
6. Save it to a file]

This demonstration shows how the pipeline structure works without requiring actual browser automation."""
        
        # Save the mock result
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"mock_response_{timestamp}"
            
        # Save response as text file
        response_file = self.output_dir / f"{output_filename}.txt"
        with open(response_file, 'w', encoding='utf-8') as f:
            f.write(f"Prompt:\n{prompt}\n\nResponse:\n{mock_response}")
            
        # Save metadata as JSON
        metadata_file = self.output_dir / f"{output_filename}.json"
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'response_length': len(mock_response),
            'response_file': str(response_file),
            'mock': True
        }
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
            
        print(f"[MOCK] Response saved to: {response_file}")
        
        # Display the result
        print("\n" + "="*80)
        print("MOCK GEMINI RESPONSE")
        print("="*80)
        print(mock_response)
        print("="*80)
        
        return response_file


async def test_direct_prompt():
    """Test using direct prompt"""
    print("Test 1: Using direct prompt")
    print("-" * 40)
    
    pipeline = MockGeminiPipeline(output_dir="./mock_output")
    result = await pipeline.run(
        prompt="Explain machine learning in simple terms",
        output_filename="ml_explanation"
    )
    
    if result:
        print(f"[OK] Test completed successfully! Result saved to: {result}")
    else:
        print("[ERROR] Test failed - no result received")
    
    return result


async def test_file_prompt():
    """Test using prompt from file"""
    print("\nTest 2: Using prompt from file")
    print("-" * 40)
    
    # Create a sample prompt file
    prompt_file = Path("test_prompt.txt")
    prompt_file.write_text("What are the benefits of using Python for data analysis?")
    
    pipeline = MockGeminiPipeline(output_dir="./mock_output")
    result = await pipeline.run(
        prompt_file=str(prompt_file),
        output_filename="python_data_analysis"
    )
    
    # Clean up
    if prompt_file.exists():
        prompt_file.unlink()
    
    if result:
        print(f"[OK] Test completed successfully! Result saved to: {result}")
    else:
        print("[ERROR] Test failed - no result received")
    
    return result


async def main():
    """Run all tests"""
    print("=" * 60)
    print("Gemini Web Chat Automation - Mock Pipeline Tests")
    print("=" * 60)
    
    # Create test output directory
    test_output_dir = Path("./mock_output")
    test_output_dir.mkdir(exist_ok=True)
    
    # Run tests
    result1 = await test_direct_prompt()
    result2 = await test_file_prompt()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print(f"Check the '{test_output_dir}' directory for results.")
    print("\nTo run the actual pipeline with real browser automation:")
    print("  python gemini_pipeline.py --prompt 'Your question here'")
    print("  python gemini_pipeline.py --prompt-file prompts.txt")
    print("  run_pipeline.bat --prompt 'Your question here'")


if __name__ == "__main__":
    asyncio.run(main())