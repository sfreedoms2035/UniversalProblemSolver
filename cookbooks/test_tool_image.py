#!/usr/bin/env python3
"""Test: Gemma should pick tool='image' for image generation."""
import asyncio
from _tool_test_base import run_test

PROMPT = (
    "Generate a photorealistic image of a futuristic quantum computer "
    "with glowing blue neon circuits and a dark laboratory background."
)

asyncio.run(run_test(PROMPT, "image"))
