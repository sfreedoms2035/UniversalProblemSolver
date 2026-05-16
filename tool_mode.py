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
    "description": "Brower-automated interface to Google Gemini (gemini.google.com). Use this tool to answer complex questions, research topics, generate text, analyze data, create images, or perform deep research via Gemini's web UI. Best for tasks needing Gemini-specific capabilities (vision, deep research, thinking mode) or when API access is unavailable. DO NOT use for simple/known facts — prefer direct API or local knowledge. Returns structured JSON with thinking/reasoning content and final answer. Supports multiple model modes and specialized tools.",
    "parameters": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The prompt to send to Gemini. Be specific and detailed for best results."
            },
            "prompt_file": {
                "type": "string",
                "description": "Path to a text file containing the prompt (alternative to prompt). Use when the prompt is very long."
            },
            "model": {
                "type": "string",
                "enum": ["fast", "thinking", "pro"],
                "description": "Gemini model mode to use. Choose based on task complexity: 'fast' for quick/trivial responses with Gemini Flash (lowest latency), 'thinking' for complex reasoning, logic, math, and multi-step problems (shows step-by-step thinking), 'pro' (default) for general-purpose tasks including advanced math, programming, and analysis with Gemini Pro."
            },
            "tool": {
                "type": "string",
                "enum": ["general", "image", "video", "canvas", "deep_research", "music", "learning", "deep_think"],
                "description": "Gemini tool to activate for the conversation. 'general' (default) for standard chat. 'image' for AI image generation (Bild erstellen). 'video' for AI video generation (Veo). 'canvas' for collaborative document/workspace editing. 'deep_research' for multi-step web research with comprehensive reports. 'music' for music generation. 'learning' for interactive learning mode. 'deep_think' for Ultra-level deep reasoning (most powerful). Note: some tools (deep_research, music, learning) require a Gemini subscription."
            },
            "tools": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Reserved for future tool toggles (currently none supported in Gemini 3.1 UI)"
            },
            "output_filename": {
                "type": "string",
                "description": "Custom output filename (without extension). Auto-generated timestamp if omitted."
            },
            "output_dir": {
                "type": "string",
                "description": "Output directory for results (default: ./output)"
            },
            "headless": {
                "type": "boolean",
                "description": "Run browser in headless mode (no visible window, default: false). Set true for automated/CI environments."
            },
            "pause_for_login": {
                "type": "boolean",
                "description": "Pause and wait for manual browser login before sending prompt (default: false). Set true on first use."
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum seconds to wait for Gemini response (default: 120). Deep Research automatically increases to min 300."
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
