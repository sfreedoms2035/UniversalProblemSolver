#!/usr/bin/env python3
"""Test: Gemma should pick tool='canvas' for collaborative workspace."""
import asyncio
from _tool_test_base import run_test

PROMPT = (
    "Open a collaborative workspace and draft a project plan for "
    "building a quantum error correction simulator, including milestones "
    "and resource allocation."
)

asyncio.run(run_test(PROMPT, "canvas"))
