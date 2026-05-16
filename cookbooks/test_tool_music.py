#!/usr/bin/env python3
"""Test: Gemma should pick tool='music' for music generation."""
import asyncio
from _tool_test_base import run_test

PROMPT = (
    "Compose a 30-second ambient electronic music track with a calm, "
    "space-inspired atmosphere and slow evolving pads."
)

asyncio.run(run_test(PROMPT, "music"))
