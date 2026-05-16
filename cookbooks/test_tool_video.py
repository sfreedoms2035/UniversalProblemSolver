#!/usr/bin/env python3
"""Test: Gemma should pick tool='video' for video generation."""
import asyncio
from _tool_test_base import run_test

PROMPT = (
    "Generate a short cinematic video of a sunset over a futuristic "
    "cyberpunk city skyline with flying cars."
)

asyncio.run(run_test(PROMPT, "video"))
