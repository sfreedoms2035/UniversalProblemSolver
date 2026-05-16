#!/usr/bin/env python3
"""
4QDR.AI Universal Problem Solver — Tool Calling with Ollama + Gemma 4

Demonstrates how a local LLM (Gemma 4 via Ollama) can semantically discover
and call the gemini_web_chat tool from our pipeline. All sub-tools (image,
video, deep_research, etc.) are registered — Gemma decides which to use based
on the prompt.

Usage:
    pip install ollama
    python cookbooks/tool_calling_with_ollama.py

Prerequisites:
    - Ollama running with gemma4:e4b (or any tool-calling model)
    - Python 3.10+
    - Run from project root (one dir up from cookbooks/)
"""

# =============================================================================
# Dependency check
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
        import importlib
        for pkg in missing:
            importlib.invalidate_caches()
    else:
        print("All dependencies found.")


ensure_dependencies()

# =============================================================================
# Jupyter compatibility
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

_SELF_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SELF_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import asyncio
import ollama
from ollama._types import ResponseError
from tool_mode import get_tool_schema, execute_tool


# =============================================================================
# Configuration
# =============================================================================

MODEL = "gemma4:e4b"

PROMPT = (
    "Research the latest advancements in quantum error correction "
    "and summarize them in 3 bullet points. "
    "Use the gemini_web_chat tool if you need real-time info from Gemini."
)

# =============================================================================
# Main flow
# =============================================================================


async def main():
    tool_schema = get_tool_schema()
    print("=" * 60)
    print("Tool schema (all sub-tools registered)")
    print("=" * 60)
    print(json.dumps(tool_schema, indent=2, ensure_ascii=False))
    print()

    ollama_tool = {
        "type": "function",
        "function": {
            "name": tool_schema["name"],
            "description": tool_schema["description"],
            "parameters": tool_schema["parameters"],
        },
    }
    print(f"Registered tool: {ollama_tool['function']['name']}")
    print()

    # --- Ask LLM ---
    messages = [{"role": "user", "content": PROMPT}]

    print("=" * 60)
    print("Asking Ollama model (all sub-tools available)")
    print("=" * 60)
    try:
        response = ollama.chat(
            model=MODEL,
            messages=messages,
            tools=[ollama_tool],
        )
    except ResponseError as e:
        print(f"  Ollama error: {e}")
        print(f"  Run: ollama pull {MODEL}")
        return

    print(f"  Model:  {response['model']}")
    print(f"  Content: {response['message']['content'] or '(tool call requested)'}")
    print()

    # --- Check tool decision ---
    tool_calls = response["message"].get("tool_calls", [])
    print("=" * 60)
    print("Gemma's tool decision")
    print("=" * 60)
    if not tool_calls:
        print("  Model answered directly without calling the tool.")
        print(f"  Answer:\n{response['message']['content']}")
        return

    for tc in tool_calls:
        args = tc["function"]["arguments"]
        args_str = json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else args
        print(f"  -> {tc['function']['name']}({args_str})")

        chosen_tool = args.get("tool", "general") if isinstance(args, dict) else "?"
        print(f"  -> Gemma chose sub-tool: '{chosen_tool}'")
    print()

    # --- Execute tool ---
    print("=" * 60)
    print("Executing tool (browser will open)")
    print("=" * 60)

    messages.append(response["message"])

    for tc in tool_calls:
        if tc["function"]["name"] != "gemini_web_chat":
            continue

        arguments = tc["function"]["arguments"]
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        arguments["headless"] = False  # Show browser

        result = await execute_tool(arguments)

        messages.append({
            "role": "tool",
            "content": json.dumps(result, ensure_ascii=False),
            "name": "gemini_web_chat",
        })
        print(f"  Tool result: success={result.get('success')}, length={result.get('response_length', 0)}")

    # --- LLM synthesis ---
    print("  Sending result back to LLM for synthesis...")
    try:
        final_response = ollama.chat(model=MODEL, messages=messages)
    except ResponseError as e:
        print(f"  Error during synthesis: {e}")
        return
    final_answer = final_response["message"]["content"]
    print()

    print("=" * 60)
    print("FINAL ANSWER FROM GEMMA 4")
    print("=" * 60)
    print(final_answer)


if __name__ == "__main__":
    asyncio.run(main())
