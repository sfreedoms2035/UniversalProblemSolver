#!/usr/bin/env python3
"""
MCP Server Mode - Exposes Gemini Pipeline as an MCP server for AI agents

This module implements a Model Context Protocol (MCP) server that exposes
the Gemini pipeline as a tool that AI agents can discover and use.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from gemini_pipeline import GeminiPipeline


# MCP Server implementation
class GeminiMCPServer:
    """MCP Server for Gemini Web Chat Pipeline"""
    
    def __init__(self):
        self.name = "gemini-web-chat"
        self.version = "1.0.0"
        self.description = "Automates interaction with Gemini web chat using Playwright"
        
    def get_server_info(self) -> dict:
        """Return server information"""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description
        }
    
    def get_tools(self) -> list:
        """Return list of available tools"""
        return [
            {
                "name": "gemini_web_chat",
                "description": "Send a prompt to Gemini web chat and get the response. Automates browser interaction with Gemini.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "The prompt to send to Gemini"
                            },
                            "prompt_file": {
                                "type": "string",
                                "description": "Path to a text file containing the prompt"
                            },
                            "model": {
                                "type": "string",
                                "enum": ["fast", "thinking", "pro"],
                                "description": "Gemini model mode: fast (quick), thinking (complex reasoning), or pro (advanced tasks, default)"
                            },
                            "tool": {
                                "type": "string",
                                "enum": ["general", "image", "video", "canvas", "deep_research", "music", "learning", "deep_think"],
                                "description": "Gemini tool: general (default), image, video, canvas, deep_research, music, learning, or deep_think (Ultra)"
                            },
                            "tools": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Reserved for future tool toggles (currently none in Gemini 3.1 UI)"
                            },
                        "output_filename": {
                            "type": "string",
                            "description": "Custom output filename (without extension)"
                        },
                        "output_dir": {
                            "type": "string",
                            "description": "Output directory for results (default: ./output)"
                        },
                        "headless": {
                            "type": "boolean",
                            "description": "Run browser in headless mode (default: true)"
                        },
                        "pause_for_login": {
                            "type": "boolean",
                            "description": "Pause for manual login (default: false)"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default: 120)"
                        }
                    },
                    "required": []
                }
            }
        ]
    
    async def call_tool(self, name: str, arguments: dict) -> dict:
        """Execute a tool call"""
        if name != "gemini_web_chat":
            return {
                "success": False,
                "error": f"Unknown tool: {name}"
            }
        
        try:
            # Extract parameters
            prompt = arguments.get('prompt')
            prompt_file = arguments.get('prompt_file')
            model = arguments.get('model', 'pro')
            tool = arguments.get('tool', 'general')
            tools = arguments.get('tools', [])
            output_filename = arguments.get('output_filename')
            output_dir = arguments.get('output_dir', './output')
            headless = arguments.get('headless', True)
            pause_for_login = arguments.get('pause_for_login', False)
            
            # Normalize tools
            if isinstance(tools, str):
                tools = [t.strip() for t in tools.split(',') if t.strip()]
            
            # Validate
            if not prompt and not prompt_file:
                return {
                    'success': False,
                    'error': 'Either prompt or prompt_file must be provided'
                }
            
            if prompt_file and not Path(prompt_file).exists():
                return {
                    'success': False,
                    'error': f'Prompt file not found: {prompt_file}'
                }
            
            # Run pipeline
            pipeline = GeminiPipeline(
                headless=headless,
                output_dir=output_dir,
                persistent=True,
                model=model,
                tool=tool,
                tools=tools
            )
            
            result = await pipeline.run(
                prompt=prompt,
                prompt_file=prompt_file,
                output_filename=output_filename,
                pause_for_login=pause_for_login,
                confirm_before_send=False,
                timeout=args.get('timeout', 300)
            )
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# MCP Protocol Message Handlers
class MCPProtocolHandler:
    """Handles MCP protocol messages"""
    
    def __init__(self, server: GeminiMCPServer):
        self.server = server
        self.message_id = 0
    
    def create_response(self, result: Any, request_id: int = None) -> dict:
        """Create an MCP response message"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
    
    def create_error(self, message: str, code: int = -32600, request_id: int = None) -> dict:
        """Create an MCP error message"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
    
    async def handle_message(self, message: dict) -> dict:
        """Handle an incoming MCP message"""
        method = message.get('method')
        request_id = message.get('id')
        params = message.get('params', {})
        
        try:
            if method == 'initialize':
                return self.create_response({
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": self.server.get_server_info()
                }, request_id)
            
            elif method == 'tools/list':
                return self.create_response({
                    "tools": self.server.get_tools()
                }, request_id)
            
            elif method == 'tools/call':
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                result = await self.server.call_tool(tool_name, arguments)
                return self.create_response(result, request_id)
            
            elif method == 'ping':
                return self.create_response({}, request_id)
            
            else:
                return self.create_error(
                    f"Method not found: {method}",
                    -32601,
                    request_id
                )
                
        except Exception as e:
            return self.create_error(str(e), -32603, request_id)


async def run_mcp_server():
    """Run the MCP server using stdio transport"""
    server = GeminiMCPServer()
    handler = MCPProtocolHandler(server)
    
    print(f"Starting MCP server: {server.name} v{server.version}", file=sys.stderr)
    print("Waiting for messages...", file=sys.stderr)
    
    # Read from stdin and write to stdout
    
    try:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                message = json.loads(line)
                response = await handler.handle_message(message)
                print(json.dumps(response))
                sys.stdout.flush()
            except json.JSONDecodeError as e:
                error_response = handler.create_error(f"Invalid JSON: {str(e)}")
                print(json.dumps(error_response))
                sys.stdout.flush()
                
    except KeyboardInterrupt:
        print("MCP server shutting down...", file=sys.stderr)
    except Exception as e:
        print(f"MCP server error: {e}", file=sys.stderr)
        sys.exit(1)


def run_mcp_mode():
    """Entry point for MCP server mode (standalone)"""
    asyncio.run(run_mcp_server())


# Example usage for testing
if __name__ == "__main__":
    print("MCP Server Mode")
    print("This module should be run as an MCP server.")
    print("Use: python mcp_server.py")
    print("\nFor testing, you can use an MCP client to connect.")
