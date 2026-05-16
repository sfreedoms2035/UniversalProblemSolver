"""
Shared base for sub-tool test scripts. Each test script sets PROMPT and
imports run_test() from here. Gemma sees ALL sub-tools in the schema and
must semantically pick the right one based on the prompt.
"""

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
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        import importlib
        for pkg in missing:
            importlib.invalidate_caches()


ensure_dependencies()

# Jupyter compat
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

MODEL = "gemma4:e4b"


async def run_test(prompt: str, label: str):
    """Run a full LLM -> tool call -> result -> synthesis test.

    Args:
        prompt: The user prompt that should steer Gemma toward a specific sub-tool.
        label: A short label like 'image', 'deep_research' for logging.
    """
    tool_schema = get_tool_schema()

    ollama_tool = {
        "type": "function",
        "function": {
            "name": tool_schema["name"],
            "description": tool_schema["description"],
            "parameters": tool_schema["parameters"],
        },
    }

    print(f"\n{'=' * 60}")
    print(f"TEST: {label}")
    print(f"{'=' * 60}")
    print(f"Model: {MODEL}")
    print(f"Prompt:\n  {prompt[:200]}...")
    print()

    # --- Ask LLM ---
    messages = [{"role": "user", "content": prompt}]

    try:
        response = ollama.chat(model=MODEL, messages=messages, tools=[ollama_tool])
    except ResponseError as e:
        print(f"  Ollama error: {e}")
        return

    tool_calls = response["message"].get("tool_calls", [])

    if not tool_calls:
        print("  Gemma answered directly without calling any tool.")
        print(f"  Answer: {response['message']['content'][:300]}")
        return

    for tc in tool_calls:
        args = tc["function"]["arguments"]
        args_str = json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else args
        chosen_tool = args.get("tool", "general") if isinstance(args, dict) else "?"
        print(f"  -> Gemma chose sub-tool: '{chosen_tool}'")
        print(f"  -> Full args: {args_str}")
    print()

    # --- Execute ---
    print("--- Executing (browser opens) ---")
    messages.append(response["message"])

    for tc in tool_calls:
        if tc["function"]["name"] != "gemini_web_chat":
            continue
        arguments = tc["function"]["arguments"]
        if isinstance(arguments, str):
            arguments = json.loads(arguments)
        arguments["headless"] = False

        result = await execute_tool(arguments)

        messages.append({
            "role": "tool",
            "content": json.dumps(result, ensure_ascii=False),
            "name": "gemini_web_chat",
        })
        print(f"  Tool result: success={result.get('success')}, length={result.get('response_length', 0)}")

    # --- Synthesis ---
    print("  Synthesizing final answer...")
    try:
        final = ollama.chat(model=MODEL, messages=messages)
    except ResponseError as e:
        print(f"  Synthesis error: {e}")
        return

    print(f"\n{'=' * 60}")
    print(f"FINAL ANSWER ({label})")
    print(f"{'=' * 60}")
    print(final["message"]["content"])
