#!/usr/bin/env python3
"""
4QDR.AI Universal Problem Solver - Main Entry Point

Modes:
  direct - Standard Python pipeline execution (default)
  tool   - Expose as callable tool for AI agents
  mcp    - Run as MCP server for AI agents

Usage:
  # Direct mode (default)
  python gemini_pipeline.py --prompt "Hello"
  
  # Tool mode
  python gemini_pipeline.py --mode tool --prompt "Hello"
  
  # MCP server mode
  python gemini_pipeline.py --mode mcp
"""

import asyncio
import json
import sys
import os
import argparse
from pathlib import Path

# 4QDR.AI Universal Problem Solver
# Copyright (c) 2025 4QDR.AI. All rights reserved.

from gemini_pipeline import GeminiPipeline


def parse_arguments():
    """Parse command line arguments with mode selection"""
    parser = argparse.ArgumentParser(
        description='4QDR.AI Universal Problem Solver',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Modes:
  direct  - Standard Python pipeline (default)
  tool    - Callable tool for AI agents
  mcp     - MCP server for AI agents

Examples:
  # Direct mode
  python main.py --prompt "Explain quantum computing"
  python main.py --prompt-file prompts.txt
  
  # Persistent mode (uses real Chrome, saves login session)
  python main.py --prompt "What is AI?" --persistent
  
  # Tool mode
  python main.py --mode tool --prompt "What is AI?"
  python main.py --mode tool --prompt-file prompts.txt --headless
  
  # MCP server mode
  python main.py --mode mcp
        '''
    )
    
    # Mode selection
    parser.add_argument('--mode', type=str, default='direct',
                       choices=['direct', 'tool', 'mcp'],
                       help='Execution mode: direct (default), tool, or mcp')
    
    # Prompt input options
    prompt_group = parser.add_mutually_exclusive_group()
    prompt_group.add_argument('--prompt', type=str, help='Prompt to send to Gemini')
    prompt_group.add_argument('--prompt-file', type=str, help='Text file containing the prompt')
    
    # Output options
    parser.add_argument('--output', type=str, help='Output filename (without extension)')
    parser.add_argument('--output-dir', type=str, default='./output', help='Output directory (default: ./output)')
    
    # Browser options
    parser.add_argument('--headless', action='store_true', help='Run browser in headless mode')
    parser.add_argument('--login', action='store_true', help='Pause for manual login before sending prompt')
    parser.add_argument('--confirm', action='store_true', help='Require manual confirmation before sending prompt (default: auto-send)')
    parser.add_argument('--persistent', action='store_true',
                       help='Save login session for next run')
    
    # Gemini configuration
    parser.add_argument('--model', type=str, default='pro', choices=['fast', 'thinking', 'pro'],
                       help='Gemini model mode: fast, thinking, or pro (default: pro)')
    parser.add_argument('--tool', type=str, default='general',
                       choices=['general', 'image', 'video', 'canvas', 'deep_research',
                                'music', 'learning', 'deep_think'],
                       help='Gemini tool to use: general (default), image, video, canvas, deep_research, music, learning, deep_think')
    parser.add_argument('--tools', type=str, default='',
                       help='Reserved for future tool toggles (currently none supported in Gemini 3.1 UI)')
    
    # Timeout
    parser.add_argument('--timeout', type=int, default=120, help='Timeout in seconds (default: 120)')
    
    # Tool/MCP specific options
    parser.add_argument('--json', action='store_true', help='Output results as JSON (tool mode)')
    parser.add_argument('--schema', action='store_true', help='Print tool schema and exit (tool mode)')
    
    return parser.parse_args()


async def run_direct_mode(args):
    """Run in direct mode - standard pipeline execution"""
    # Validate prompt
    if not args.prompt and not args.prompt_file:
        print("Error: Either --prompt or --prompt-file must be provided in direct mode")
        sys.exit(1)
    
    if args.prompt_file and not os.path.exists(args.prompt_file):
        print(f"Error: Prompt file '{args.prompt_file}' not found")
        sys.exit(1)
    
    # Initialize and run pipeline
    pipeline = GeminiPipeline(
        headless=args.headless,
        output_dir=args.output_dir,
        persistent=args.persistent,
        model=args.model,
        tool=args.tool,
        tools=[t.strip() for t in args.tools.split(',') if t.strip()]
    )
    
    try:
        result = await pipeline.run(
            prompt=args.prompt,
            prompt_file=args.prompt_file,
            output_filename=args.output,
            pause_for_login=args.login,
            confirm_before_send=args.confirm,
            timeout=args.timeout
        )
        
        if result.get('success'):
            print(f"\nPipeline completed successfully!")
            print(f"Result saved to: {result.get('response_file')}")
        else:
            print(f"\nPipeline failed: {result.get('error')}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nPipeline failed: {e}")
        sys.exit(1)


async def run_tool_mode(args):
    """Run in tool mode - callable tool for AI agents"""
    from tool_mode import execute_tool, get_tool_schema
    
    # If --schema flag, output tool schema
    if hasattr(args, 'schema') and args.schema:
        print(json.dumps(get_tool_schema(), indent=2))
        return
    
    # Prepare arguments for tool execution
    tool_args = {
        'prompt': args.prompt,
        'prompt_file': args.prompt_file,
        'output_filename': args.output,
        'output_dir': args.output_dir,
        'headless': args.headless if args.headless else True,  # Default to headless for tool mode
        'pause_for_login': args.login,
        'model': args.model,
        'tool': args.tool,
        'tools': args.tools,
        'timeout': args.timeout
    }
    
    # Execute tool
    result = await execute_tool(tool_args)
    
    # Output result
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get('success'):
            print(f"Tool execution successful!")
            print(f"Response: {result.get('response', '')[:200]}...")
            print(f"Saved to: {result.get('response_file')}")
        else:
            print(f"Tool execution failed: {result.get('error')}")
            sys.exit(1)


async def run_mcp_mode(args):
    """Run in MCP server mode"""
    from mcp_server import run_mcp_server
    await run_mcp_server()


async def main():
    """Main entry point with mode selection"""
    args = parse_arguments()
    
    # Route to appropriate mode
    if args.mode == 'direct':
        await run_direct_mode(args)
    elif args.mode == 'tool':
        await run_tool_mode(args)
    elif args.mode == 'mcp':
        await run_mcp_mode(args)
    else:
        print(f"Unknown mode: {args.mode}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
