#!/usr/bin/env python3
"""
4QDR.AI Universal Problem Solver — MCP Client Usage

Demonstrates how to connect to the MCP server (mcp_server.py) via stdio JSON-RPC,
list available tools, and call them programmatically.

Usage:
    python cookbooks/mcp_client_usage.py

Prerequisites:
    - Python 3.10+ (stdlib only — no extra packages needed)
    - A valid Gemini session (run 'python -m main --login' once first)
    - Run from project root (one dir up from cookbooks/)
"""

# =============================================================================
# Dependency check — stdlib only, but needs project sibling imports
# =============================================================================
import sys
import os
from pathlib import Path

_SELF_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = Path(_SELF_DIR).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# =============================================================================
# Imports
# =============================================================================
import asyncio
import json
import subprocess
from pathlib import Path

# =============================================================================
# Minimal MCP client
# =============================================================================


class MCPClient:
    """Minimal MCP client over stdio JSON-RPC."""

    def __init__(self, server_script: str | Path):
        self.server_script = Path(server_script)
        self.proc: subprocess.Popen | None = None
        self._request_id = 0

    def start(self):
        """Launch the MCP server subprocess."""
        self.proc = subprocess.Popen(
            [sys.executable, str(self.server_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=str(self.server_script.parent),
        )
        print(f"  MCP server started (PID: {self.proc.pid})")

    def send_request(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request and return the response."""
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {},
        }
        request_line = json.dumps(request)
        print(f"  >> {method} (id={self._request_id})")

        self.proc.stdin.write(request_line + "\n")
        self.proc.stdin.flush()

        response_line = self.proc.stdout.readline().strip()
        if not response_line:
            raise ConnectionError(
                "MCP server closed connection. The session may have expired "
                "— run 'python -m main --login' first."
            )

        return json.loads(response_line)

    def close(self):
        """Terminate the MCP server."""
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
            print(f"  MCP server terminated (PID: {self.proc.pid})")


# =============================================================================
# Full async example — end-to-end
# =============================================================================


async def call_gemini_via_mcp(
    server_script: str | Path,
    prompt: str,
    timeout: int = 120,
) -> dict:
    """Send a prompt to Gemini via the MCP server in a single call."""
    c = MCPClient(server_script)
    try:
        c.start()

        # Initialize
        c.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "mcp-client", "version": "1.0.0"},
            },
        )

        # Call tool
        resp = c.send_request(
            "tools/call",
            {
                "name": "gemini_web_chat",
                "arguments": {
                    "prompt": prompt,
                    "headless": True,
                    "timeout": timeout,
                },
            },
        )

        return resp.get("result", {})
    finally:
        c.close()


# =============================================================================
# Main
# =============================================================================


async def main():
    server_path = _PROJECT_ROOT / "mcp_server.py"

    print("=" * 60)
    print("MCP CLIENT DEMONSTRATION")
    print("=" * 60)
    print()

    # ------------------------------------------------------------------
    # Step 1: Launch the MCP server
    # ------------------------------------------------------------------
    print("--- Step 1: Launch MCP server ---")
    client = MCPClient(server_path)
    client.start()
    print()

    # ------------------------------------------------------------------
    # Step 2: Initialize the connection
    # ------------------------------------------------------------------
    print("--- Step 2: Initialize ---")
    init_response = client.send_request(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "mcp-cookbook-client", "version": "1.0.0"},
        },
    )
    print(json.dumps(init_response, indent=2, ensure_ascii=False))
    print()

    # ------------------------------------------------------------------
    # Step 3: List available tools
    # ------------------------------------------------------------------
    print("--- Step 3: List tools ---")
    tools_response = client.send_request("tools/list")
    tools = tools_response.get("result", {}).get("tools", [])
    print(f"  Available tools: {len(tools)}")
    for t in tools:
        print(f"    Name:        {t['name']}")
        desc = t.get("description", "")
        print(f"    Description: {desc[:120]}...")
        props = t.get("inputSchema", {}).get("properties", {})
        print(f"    Parameters:  {', '.join(props.keys())}")
    print()

    # ------------------------------------------------------------------
    # Step 4: Call the tool
    # ------------------------------------------------------------------
    print("--- Step 4: Call gemini_web_chat ---")
    call_response = client.send_request(
        "tools/call",
        {
            "name": "gemini_web_chat",
            "arguments": {
                "prompt": "What are the three laws of robotics?",
                "model": "fast",
                "tool": "general",
                "headless": True,
                "timeout": 60,
            },
        },
    )
    result = call_response.get("result", {})
    print(f"  Success:  {result.get('success')}")
    print(f"  Model:    {result.get('model')}")
    print(f"  Duration: {result.get('duration', 0):.1f}s")
    print(f"  Answer preview: {result.get('response', '')[:300]}...")
    print()

    # ------------------------------------------------------------------
    # Step 5: Health check
    # ------------------------------------------------------------------
    print("--- Step 5: Ping ---")
    ping_response = client.send_request("ping")
    print(f"  Ping result: {ping_response.get('result')}")
    print()

    # ------------------------------------------------------------------
    # Step 6: Cleanup
    # ------------------------------------------------------------------
    print("--- Step 6: Cleanup ---")
    client.close()
    print()

    # ------------------------------------------------------------------
    # Bonus: One-shot convenience function
    # ------------------------------------------------------------------
    print("--- Bonus: One-shot call via call_gemini_via_mcp() ---")
    one_shot = await call_gemini_via_mcp(
        server_path,
        "What is the speed of light in km/s?",
        timeout=60,
    )
    print(f"  Success:  {one_shot.get('success')}")
    print(f"  Response: {one_shot.get('response', '')[:200]}...")
    print()

    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
