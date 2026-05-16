#!/usr/bin/env python3
"""
Demo script showing how to use the GeminiPipeline programmatically.
"""

import asyncio
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from gemini_pipeline import GeminiPipeline


async def demo_direct_prompt():
    """Demo using direct prompt"""
    print("Demo 1: Using direct prompt")
    
    pipeline = GeminiPipeline(headless=True, output_dir="./demo_output")
    
    try:
        result = await pipeline.run(
            prompt="What is Python programming language? Give me a brief explanation.",
            output_filename="python_explanation"
        )
        
        if result:
            print(f"✓ Demo completed successfully! Result saved to: {result}")
        else:
            print("✗ Demo failed - no result received")
            
    except Exception as e:
        print(f"✗ Demo failed with error: {e}")


async def demo_file_prompt():
    """Demo using prompt from file"""
    print("Demo 2: Using prompt from file")
    
    # Create a sample prompt file
    prompt_file = Path("demo_prompt.txt")
    prompt_file.write_text("Explain the concept of object-oriented programming in 3 sentences.")
    
    pipeline = GeminiPipeline(headless=True, output_dir="./demo_output")
    
    try:
        result = await pipeline.run(
            prompt_file=str(prompt_file),
            output_filename="oop_explanation"
        )
        
        if result:
            print(f"✓ Demo completed successfully! Result saved to: {result}")
        else:
            print("✗ Demo failed - no result received")
            
    finally:
        # Clean up demo file
        if prompt_file.exists():
            prompt_file.unlink()


async def demo_batch_prompts():
    """Demo using multiple prompts"""
    print("Demo 3: Batch processing multiple prompts")
    
    prompts = [
        "What is machine learning?",
        "Explain cloud computing in simple terms.",
        "What are the benefits of using Python?"
    ]
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\nProcessing prompt {i}/{len(prompts)}: {prompt[:30]}...")
        
        pipeline = GeminiPipeline(headless=True, output_dir="./demo_output")
        
        try:
            result = await pipeline.run(
                prompt=prompt,
                output_filename=f"response_{i}"
            )
            
            if result:
                print(f"✓ Prompt {i} completed! Result saved to: {result}")
            else:
                print(f"✗ Prompt {i} failed - no result received")
                
        except Exception as e:
            print(f"✗ Prompt {i} failed with error: {e}")


async def main():
    """Run all demos"""
    print("=" * 60)
    print("Gemini Web Chat Automation - Demo Scripts")
    print("=" * 60)
    
    # Create demo output directory
    demo_output_dir = Path("./demo_output")
    demo_output_dir.mkdir(exist_ok=True)
    
    # Run demos
    await demo_direct_prompt()
    
    print("\n" + "-" * 60)
    
    await demo_file_prompt()
    
    print("\n" + "-" * 60)
    
    # Uncomment the line below to run batch demo (requires multiple API calls)
    # await demo_batch_prompts()
    
    print("\n" + "=" * 60)
    print("All demos completed!")
    print("Check the './demo_output' directory for results.")


if __name__ == "__main__":
    asyncio.run(main())