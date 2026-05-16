#!/usr/bin/env python3
"""Test: Gemma should pick tool='deep_think' for ultra-level reasoning."""
import asyncio
from _tool_test_base import run_test

PROMPT = (
    "Analyze the philosophical implications of quantum decoherence "
    "on the measurement problem in quantum mechanics. Provide a deep, "
    "multi-perspective analysis."
)

asyncio.run(run_test(PROMPT, "deep_think"))
