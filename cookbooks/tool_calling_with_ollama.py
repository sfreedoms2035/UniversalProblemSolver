#!/usr/bin/env python3
"""
4QDR.AI Universal Problem Solver — Tool Calling with Ollama + Gemma 4

Demonstrates how a local LLM (Gemma 4 via Ollama) can semantically discover
and call the gemini_web_chat tool from our pipeline.

Usage:
    pip install ollama
    python cookbooks/tool_calling_with_ollama.py

Prerequisites:
    - Ollama running locally with a tool-calling model pulled (gemma4, qwen3, llama3.1+, etc.)
    - Python 3.10+
    - Run from project root (one dir up from cookbooks/)
"""

# =============================================================================
# Dependency check — install missing packages automatically
# =============================================================================
import subprocess
import sys

REQUIRED_PACKAGES = ["ollama", "playwright"]


def ensure_dependencies():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg.replace("-", "_"))
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *missing]
        )
        print("Dependencies installed.")
        # Force reimport after install
        import importlib
        for pkg in missing:
            importlib.invalidate_caches()
    else:
        print("All dependencies found.")


ensure_dependencies()

# =============================================================================
# Jupyter compatibility — patch missing sys.stdout.buffer
# =============================================================================
if not hasattr(sys.stdout, "buffer"):

    class _DummyBuffer:
        def write(self, b):
            sys.stdout.write(b.decode("utf-8", "replace"))
            return len(b)

        def flush(self):
            sys.stdout.flush()

        def readable(self):
            return False

        def writable(self):
            return True

        def seekable(self):
            return False

    sys.stdout.buffer = _DummyBuffer()


# =============================================================================
# Imports
# =============================================================================
import json
import os
import subprocess as _subprocess
import argparse

# Ensure project root is on sys.path so tool_mode is importable
_SELF_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SELF_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import asyncio
import ollama
from ollama._types import ResponseError
from tool_mode import get_tool_schema, execute_tool


# =============================================================================
# Tool-specific prompts
# =============================================================================

TOOL_PROMPTS = {
    "general": (
        "Research the latest advancements in quantum error correction "
        "and summarize them in 3 bullet points."
    ),
    "deep_research": (
        "Research the latest advancements in quantum error correction "
        "and produce a comprehensive multi-source research report with citations."
    ),
    "image": (
        "Generate a photorealistic image of a futuristic quantum computer "
        "with glowing circuits in a blue neon style."
    ),
    "video": (
        "Generate a short cinematic video of a sunset over a futuristic city skyline."
    ),
    "canvas": (
        "Open a collaborative workspace and draft a project plan for "
        "building a quantum error correction simulator."
    ),
    "music": (
        "Compose a 30-second ambient electronic track with a calm, "
        "space-inspired atmosphere."
    ),
    "learning": (
        "Help me understand the concept of quantum superposition "
        "with an interactive step-by-step explanation."
    ),
    "deep_think": (
        "Analyze the philosophical implications of quantum decoherence "
        "on the measurement problem in quantum mechanics."
    ),
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Test gemini_web_chat with Gemma 4 via Ollama"
    )
    parser.add_argument(
        "--tool", type=str, default="general",
        choices=list(TOOL_PROMPTS.keys()),
        help="Gemini sub-tool to test (default: general)"
    )
    return parser.parse_args()


# =============================================================================
# Model configuration
# =============================================================================

MODEL = "gemma4:e4b"


# =============================================================================
# Main flow
# =============================================================================


async def main():
    args = parse_args()
    tool_name = args.tool
    prompt_text = TOOL_PROMPTS[tool_name]

    # ------------------------------------------------------------------
    # Step 1: Inspect the tool schema
    # Step 1: Inspect the tool schema
    # ------------------------------------------------------------------
    tool_schema = get_tool_schema()
    print("=" * 60)
    print("STEP 1 — Tool schema")
    print("=" * 60)
    print(json.dumps(tool_schema, indent=2, ensure_ascii=False))
    print()

    # ------------------------------------------------------------------
    # Step 2: Convert to Ollama-compatible tool format
    # ------------------------------------------------------------------
    ollama_tool = {
        "type": "function",
        "function": {
            "name": tool_schema["name"],
            "description": tool_schema["description"],
            "parameters": tool_schema["parameters"],
        },
    }
    print("=" * 60)
    print("STEP 2 — Registered tool for Ollama")
    print("=" * 60)
    print(f"  Name:        {ollama_tool['function']['name']}")
    print(f"  Description: {ollama_tool['function']['description'][:100]}...")
    print()

    # ------------------------------------------------------------------
    # Step 3: Send query to Gemma 4 with tool access
    # ------------------------------------------------------------------
    messages = [
        {
            "role": "user",
            "content": (
                f"{prompt_text}\n\n"
                f"IMPORTANT: Use the gemini_web_chat tool with tool='{tool_name}' to accomplish this."
            ),
        }
    ]

    print("=" * 60)
    print(f"STEP 3 — Asking Ollama model (tool='{tool_name}')")
    print("=" * 60)
    try:
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            tools=[ollama_tool],
        )
    except ResponseError as e:
        print(f"  ✗ Ollama error: {e}")
        print()
        print("  Tips:")
        print(f"    - Run: ollama pull {MODEL}")
        if "memory" in str(e).lower():
            print("    - Not enough system memory. Close other apps or restart Ollama.")
        print()
        return
    print(f"  Model:  {response['model']}")
    print(f"  Role:   {response['message']['role']}")
    print(f"  Content: {response['message']['content'] or '(tool call requested)'}")
    print()

    # ------------------------------------------------------------------
    # Step 4: Check if the model wants to call the tool
    # ------------------------------------------------------------------
    tool_calls = response["message"].get("tool_calls", [])
    print("=" * 60)
    print("STEP 4 — Tool call decision")
    print("=" * 60)
    if not tool_calls:
        print("  Model answered directly without calling the tool.")
        print(f"  Final answer:\n{response['message']['content']}")
        return
    else:
        print(f"  Model requested {len(tool_calls)} tool call(s):")
        for tc in tool_calls:
            args = tc["function"]["arguments"]
            print(f"    - {tc['function']['name']}({json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else args})")
    print()

    # ------------------------------------------------------------------
    # Step 5: Execute the tool & return results to the LLM
    # ------------------------------------------------------------------
    print("=" * 60)
    print(f"STEP 5 — Executing tool & feeding result back to LLM (tool='{tool_name}')")
    print("=" * 60)

    # Append the model's tool-call response
    messages.append(response["message"])

    for tc in tool_calls:
        if tc["function"]["name"] != "gemini_web_chat":
            print(f"  Skipping unknown tool: {tc['function']['name']}")
            continue

        arguments = tc["function"]["arguments"]
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        preview = arguments.get("prompt", "")[:60]
        print(f"  Executing gemini_web_chat(prompt='{preview}...', tool='{tool_name}')")

        # Show browser so you can watch the automation
        arguments["headless"] = False
        # Force the requested sub-tool regardless of what the LLM chose
        arguments["tool"] = tool_name

        # This opens Playwright, navigates to Gemini, sends the prompt
        result = await execute_tool(arguments)

        messages.append(
            {
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False),
                "name": "gemini_web_chat",
            }
        )
        success = result.get("success")
        length = result.get("response_length", 0)
        print(f"  Tool result: success={success}, response_length={length}")

    # Send the full conversation back to the LLM for synthesis
    print("  Sending conversation to LLM for final synthesis...")
    try:
        final_response = ollama.chat(
            model=MODEL,
            messages=messages,
        )
    except ResponseError as e:
        print(f"  ✗ Ollama error during synthesis: {e}")
        print(f"  Tool result was still saved to disk.")
        return
    final_answer = final_response["message"]["content"]
    print()

    # ------------------------------------------------------------------
    # Step 6: View the final answer
    # ------------------------------------------------------------------
    print("=" * 60)
    print(f"FINAL ANSWER FROM GEMMA 4 (tool='{tool_name}')")
    print("=" * 60)
    print(final_answer)
    print()


if __name__ == "__main__":
    asyncio.run(main())
