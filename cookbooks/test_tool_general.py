#!/usr/bin/env python3
"""Test: Gemma should pick tool='general' for a standard Q&A question."""
import asyncio
from _tool_test_base import run_test

PROMPT = (
    "Research the latest advancements in quantum error correction "
    "and summarize them in 3 bullet points."
)

asyncio.run(run_test(PROMPT, "general"))
