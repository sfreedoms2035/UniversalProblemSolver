#!/usr/bin/env python3
"""Test: Gemma should pick tool='deep_research' for multi-step web research."""
import asyncio
from _tool_test_base import run_test

PROMPT = (
    "Research the latest breakthroughs in quantum error correction. "
    "Do a thorough multi-source investigation and produce a comprehensive "
    "research report with citations from recent papers."
)

asyncio.run(run_test(PROMPT, "deep_research"))
