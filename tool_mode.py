#!/usr/bin/env python3
"""
4QDR.AI Universal Problem Solver - Tool Mode

This module provides a tool interface that AI agents can use to invoke the pipeline.
It returns structured JSON responses suitable for programmatic consumption.
"""

import asyncio
import json
import sys
from pathlib import Path

# 4QDR.AI Universal Problem Solver
# Copyright (c) 2025 4QDR.AI. All rights reserved.

from gemini_pipeline import GeminiPipeline


# Tool definition for AI agents
TOOL_DEFINITION = {
    "name": "gemini_web_chat",
    "description": "Automates interaction with Gemini web chat using Playwright. Sends prompts to Gemini, captures responses, and saves results.",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The prompt to send to Gemini"
            },
            "prompt_file": {
                "type": "string",
                "description": "Path to a text file containing the prompt (alternative to prompt)"
            },
            "model": {
                "type": "string",
                "enum": ["fast", "thinking", "pro"],
                "description": "Gemini model mode: fast (quick responses), thinking (complex reasoning), or pro (advanced math/programming, default)"
            },
            "tool": {
                "type": "string",
                "enum": ["general", "image", "video", "canvas", "deep_research", "music", "learning", "deep_think"],
                "description": "Gemini tool: general (default), image (Bild erstellen), video (Video erstellen), canvas, deep_research, music, learning, or deep_think (Ultra)"
            },
            "tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Reserved for future tool toggles (currently none supported in Gemini 3.1 UI)"
            },
            "output_filename": {
                "type": "string",
                "description": "Custom output filename (without extension)"
            },
            "output_dir": {
                "type": "string",
                "description": "Output directory for results (default: ./output)"
            },
            "headless": {
                "type": "boolean",
                "description": "Run browser in headless mode (default: false)"
            },
            "pause_for_login": {
                "type": "boolean",
                "description": "Pause for manual login before sending prompt (default: false)"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds for Gemini response (default: 120)"
            }
        },
        "required": []
    }
}


async def execute_tool(arguments: dict) -> dict:
    """
    Execute the Gemini pipeline as a tool.
    
    Args:
        arguments: Dictionary containing tool parameters
        
    Returns:
        Dictionary with execution results
    """
    try:
        # Extract parameters with defaults
        prompt = arguments.get('prompt')
        prompt_file = arguments.get('prompt_file')
        model = arguments.get('model', 'pro')
        tool = arguments.get('tool', 'general')
        tools = arguments.get('tools', [])
        output_filename = arguments.get('output_filename')
        output_dir = arguments.get('output_dir', './output')
        headless = arguments.get('headless', True)  # Default to headless for tool mode
        pause_for_login = arguments.get('pause_for_login', False)
        timeout = arguments.get('timeout', 120)
        
        # Validate model
        if model not in ('fast', 'thinking', 'pro'):
            return {
                'success': False,
                'error': f"Invalid model '{model}'. Must be 'fast', 'thinking', or 'pro'",
                'tool': 'gemini_web_chat'
            }
        
        # Validate tool
        valid_tools = ('general', 'image', 'video', 'canvas', 'deep_research', 'music', 'learning', 'deep_think')
        if tool not in valid_tools:
            return {
                'success': False,
                'error': f"Invalid tool '{tool}'. Must be one of: {', '.join(valid_tools)}",
                'tool': 'gemini_web_chat'
            }
        
        # Validate tools (reserved for future use)
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(',') if t.strip()]
        if tools:
            print(f"Note: Tools parameter '{tools}' is reserved for future use. "
                  f"Web search is model-integrated in Gemini 3.1.")
        
        # Validate input
        if not prompt and not prompt_file:
            return {
                'success': False,
                'error': 'Either prompt or prompt_file must be provided',
                'tool': 'gemini_web_chat'
            }
        
        if prompt_file and not Path(prompt_file).exists():
            return {
                'success': False,
                'error': f'Prompt file not found: {prompt_file}',
                'tool': 'gemini_web_chat'
            }
        
        # Initialize and run pipeline
        pipeline = GeminiPipeline(
            headless=headless,
            output_dir=output_dir,
            persistent=True,
            model=model,
            tool=tool,
            tools=tools
        )
        
        result = await pipeline.run(
            prompt=prompt,
            prompt_file=prompt_file,
            output_filename=output_filename,
            pause_for_login=pause_for_login,
            confirm_before_send=False,  # No confirmation in tool mode
            timeout=timeout
        )
        
        # Add tool metadata
        result['agent_tool'] = 'gemini_web_chat'
        
        return result
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'tool': 'gemini_web_chat'
        }


def get_tool_schema() -> dict:
    """Return the tool schema for AI agent registration"""
    return TOOL_DEFINITION


def run_tool_mode(arguments: dict) -> str:
    """
    Run tool mode synchronously and return JSON result.
    
    Args:
        arguments: Dictionary containing tool parameters
        
    Returns:
        JSON string with execution results
    """
    result = asyncio.run(execute_tool(arguments))
    return json.dumps(result, indent=2, ensure_ascii=False)


# Example usage for testing
if __name__ == "__main__":
    # Test with sample arguments
    test_args = {
        "prompt": "What is machine learning?",
        "output_filename": "test_tool_mode",
        "headless": True
    }
    
    print("Testing tool mode...")
    result = run_tool_mode(test_args)
    print(result)
