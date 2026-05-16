#!/usr/bin/env python3
"""Test: Gemma should pick tool='learning' for interactive learning."""
import asyncio
from _tool_test_base import run_test

PROMPT = (
    "Help me understand the concept of quantum superposition "
    "with an interactive step-by-step explanation and quizzes."
)

asyncio.run(run_test(PROMPT, "learning"))
