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
# Model auto-detection
# =============================================================================

# Models known to support tool/function calling in Ollama
# Format: (family_prefix, min_size_gb_estimate) for memory guidance
TOOL_CAPABLE_MODELS = {
    # family       min_gb  notes
    "gemma4":       5.0,   # Gemma 4 — first Gemma with tool calling
    "llama4":       5.0,   # Llama 4 (Scout/Maverick)
    "llama3.3":     4.0,   # Llama 3.3 70B (needs lots of RAM, quantized variants exist)
    "llama3.2":     2.5,   # Llama 3.2 (1B/3B — small! but tool support is limited)
    "llama3.1":     4.0,   # Llama 3.1 8B
    "qwen3":        2.5,   # Qwen 3 (1.7B/4B/8B/14B/32B — 1.7B works with ~2 GiB)
    "mistral":      4.0,   # Mistral v0.3+
    "mixtral":      4.0,   # Mixtral 8x7B
    "phi4":         3.0,   # Phi-4 (14B — 3 GiB quantized)
    "command-r":    4.0,   # Cohere Command R+
    "deepseek":     4.0,   # DeepSeek V2+
    "nemotron":     4.0,   # NVIDIA Nemotron
    "hermes3":      4.0,   # Hermes 3
    "dolphin":      4.0,   # Dolphin 3
}


def _model_family(name: str) -> str:
    """Extract base family from a model tag like 'gemma4:e4b' → 'gemma4'."""
    return name.split(":")[0].split("-")[0].split(".")[0].rstrip("0123456789")


def _is_tool_capable(name: str) -> bool:
    """Check if model is known to support tool calling.

    Uses prefix matching so 'gemma4:e4b' matches 'gemma4', but 'gemma3:1b' does NOT.
    """
    name_lower = name.lower()
    for family in TOOL_CAPABLE_MODELS:
        # Match full family prefix (gemma4 matches, gemma3 does not)
        if name_lower.startswith(family.lower()):
            # Make sure it's not a sub-match: gemma4 matches gemma4 but not gemma3
            rest = name_lower[len(family):]
            if not rest or rest.startswith(":") or rest.startswith("-"):
                return True
    return False


def _get_available_models() -> list[dict]:
    """Return list of locally pulled Ollama models with tool-calling support."""
    try:
        models = ollama.list().get("models", [])
    except Exception:
        return []

    candidates = []
    for m in models:
        name = m.get("model", "")
        if _is_tool_capable(name):
            size_gb = m.get("size", 0) / (1024**3)
            candidates.append({"name": name, "size_gb": round(size_gb, 1)})

    # Sort by size ascending (prefer smaller models when memory is tight)
    candidates.sort(key=lambda c: c["size_gb"])
    return candidates


def _estimate_available_memory_gb() -> float:
    """Return estimated available system memory in GiB."""
    try:
        if sys.platform == "win32":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            mem = ctypes.c_ulonglong(0)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            # MEMORYSTATUSEX has ullAvailPhys at offset 24 (8 bytes)
            # Simpler approach: use psutil if available
            try:
                import psutil

                return round(psutil.virtual_memory().available / (1024**3), 1)
            except ImportError:
                pass
        elif sys.platform in ("linux", "darwin"):
            try:
                import psutil

                return round(psutil.virtual_memory().available / (1024**3), 1)
            except ImportError:
                pass
    except Exception:
        pass
    return 0.0


def _print_available_models(candidates: list[dict], available_gb: float):
    """Print available tool-capable models and their sizes."""
    if not candidates:
        print("  No tool-capable models found locally.")
        print("  Pull one with: ollama pull gemma4  (or qwen3, llama3.1, etc.)")
        return

    print(f"  Available models (system memory: ~{available_gb:.1f} GiB free):")
    for c in candidates:
        fits = "✓" if c["size_gb"] <= available_gb else "✗ insufficient memory"
        print(f"    {c['name']:<30s} {c['size_gb']:>5.1f} GiB  {fits}")


def pick_model(override: str | None = None) -> str:
    """
    Pick the best available Ollama model for tool calling.

    1. If ``--model`` was passed on the CLI, use that (no checks)
    2. Otherwise scan local models, pick the smallest tool-capable one that
       fits in available memory
    3. Fall back to ``gemma4:e4b`` (user may need to pull it)
    """
    if override:
        return override

    candidates = _get_available_models()
    available_gb = _estimate_available_memory_gb()

    print("=" * 60)
    print("Model Detection")
    print("=" * 60)

    _print_available_models(candidates, available_gb)

    # Pick smallest model that fits in available memory
    for c in candidates:
        if available_gb == 0.0 or c["size_gb"] <= available_gb:
            chosen = c["name"]
            print(f"\n  → Selected: {chosen} ({c['size_gb']} GiB)")
            print()
            return chosen

    # No model fits
    if candidates:
        smallest = candidates[0]
        print(
            f"\n  ⚠  '{smallest['name']}' needs ~{smallest['size_gb']} GiB but only "
            f"{available_gb:.1f} GiB is free."
        )
        print("     Try closing other applications or use a smaller model.")

    print(f"\n  ⚠  No tool-capable model fits in available memory ({available_gb:.1f} GiB).")
    print(f"     Pull a lightweight tool-capable model like:")
    print(f"       ollama pull qwen3:1.7b    (~1.4 GiB, good tool support)")
    print(f"       ollama pull llama3.2:3b   (~2.0 GiB)")
    print()
    return None


# =============================================================================
# Main flow
# =============================================================================


async def main():
    # --- Parse optional CLI override for model ---
    model_override = None
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--model" and i + 1 < len(sys.argv):
            model_override = sys.argv[i + 1]

    MODEL = pick_model(model_override)
    if MODEL is None:
        print("No suitable model available. Exiting.")
        print("Tip: ollama pull qwen3:1.7b  (small, tool-capable)")
        sys.exit(1)

    # ------------------------------------------------------------------
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
                "Research the latest advancements in quantum error correction "
                "and summarize them in 3 bullet points. "
                "Use the gemini_web_chat tool if you need real-time info from Gemini."
            ),
        }
    ]

    print("=" * 60)
    print("STEP 3 — Asking Ollama model (with tools available)")
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
        print(f"    - The model '{MODEL}' may not be pulled yet. Run: ollama pull {MODEL}")
        if "memory" in str(e).lower():
            print("    - Not enough system memory. Try a smaller model like qwen3:1.7b")
            print("      or pass --model <name> to override.")
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
    print("STEP 5 — Executing tool & feeding result back to LLM")
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
        print(f"  Executing gemini_web_chat(prompt='{preview}...')")

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
    print("STEP 6 — Final answer from Gemma 4")
    print("=" * 60)
    print(final_answer)
    print()


if __name__ == "__main__":
    asyncio.run(main())
