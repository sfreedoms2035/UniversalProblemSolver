# Gemini Web Chat Automation Pipeline

Automates interaction with Gemini web chat using Playwright. Accepts prompts (directly or from files), sends them to Gemini, captures the full response (including thinking/reasoning), and saves structured results as JSON.

## Features

- **Multi-Mode System**: Three operation modes — direct, tool, MCP
- **Model Selection**: Switch between Fast, Thinking-Modus, and Pro modes
- **Tool Selection**: Activate Gemini tools — image generation, video, Canvas, Deep Research, music, learning, Deep Think
- **Tool Availability Detection**: Automatically detects if tools are disabled due to plan/rate limits
- **Session Persistence**: Saves login state to avoid repeated manual login
- **Thinking Extraction**: Separates Gemini's thought process from the answer
- **Structured JSON Output**: Timestamp, prompt, thinking, answer, model, tool, duration
- **Console Visualization**: Clean display of thinking, answer, and active tool
- **Tool Mode**: Callable interface for AI agents with JSON schema
- **MCP Server**: Model Context Protocol server for agent frameworks
- **Overlay Dismissal**: Automatically handles popups, dialogs, and banners
- **Anti-Detection**: Uses real Chrome with stealth launch arguments

## Installation

1. **Prerequisites**: Python 3.7+, Google Chrome installed

2. **Setup virtual environment and install dependencies:**
```batch
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
python -m playwright install chromium
```

Or use the shortcut:
```batch
run_pipeline.bat   # auto-creates venv and installs
```

## Usage

### Quick Start

```batch
:: First run — log in manually (browser stays open)
python main.py --prompt "Hello" --login

:: Subsequent runs — session persists automatically
python main.py --prompt "Explain quantum computing" --no-confirm

:: With model and tool selection
python main.py --prompt "Latest AI news" --model thinking --no-confirm

:: With a Gemini tool (Canvas, Deep Research, etc.)
python main.py --prompt "create a todo app" --model pro --tool canvas --no-confirm

:: Headless mode (session required)
python main.py --prompt "What is Python?" --model pro --headless --no-confirm
```

### Session Management

The session is **auto-loaded** if `output/gemini_session.json` exists. On first run:

1. Run once without `--persistent` to log in manually
2. The session is **automatically saved** after a successful run
3. Future runs load the session automatically — no re-login needed

If the session expires, add `--login` to force a re-login:

```batch
python main.py --prompt "Hello" --login
```

### First Login Flow

On first run, the browser opens to Gemini's login page. After you log in, the pipeline detects the chat interface and proceeds. The session is saved to `output/gemini_session.json` for future use.

---

## Direct Mode (default)

Run the pipeline directly from the command line:

```batch
:: Basic prompt
python main.py --prompt "Explain machine learning"

:: From a file
python main.py --prompt-file my_prompt.txt

:: Model selection
python main.py --prompt "Complex math problem" --model thinking

:: With session save and no confirmation
python main.py --prompt "Hello" --persistent --no-confirm

:: Custom output
python main.py --prompt "AI" --output my_result --output-dir ./results

:: Headless (Chrome not visible)
python main.py --prompt "Hi" --headless

:: Longer timeout for complex responses
python main.py --prompt "Write a book" --timeout 300
```

### Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--prompt TEXT` | Prompt to send to Gemini | — |
| `--prompt-file FILE` | Read prompt from text file | — |
| `--model {fast,thinking,pro}` | Gemini model mode | `pro` |
| `--tool {general,image,video,canvas,deep_research,music,learning,deep_think}` | Gemini tool to activate | `general` |
| `--tools LIST` | Reserved for future use | `""` |
| `--headless` | Run browser headless (no visible window) | `false` |
| `--persistent` | Save login session for next run | `false` |
| `--login` | Pause for manual login before sending | `false` |
| `--no-confirm` | Skip "press ENTER to send" confirmation | `false` |
| `--output FILE` | Custom output filename (no extension) | auto |
| `--output-dir DIR` | Output directory | `./output` |
| `--timeout SEC` | Response wait timeout | `120` |

### Model Modes

| Mode | Description |
|------|-------------|
| `pro` | Gemini 3.1 Pro — complex math, programming, advanced tasks |
| `thinking` | Thinking-Modus — complex reasoning, multi-step problems |
| `fast` | Fast model — quick responses, simple queries |

### Tools

Select a Gemini-specific tool instead of general chat. Tools are selected from the toolbox drawer (or model menu for Deep Think). Availability depends on your Google account plan and rate limits — the pipeline automatically detects and reports disabled tools.

| Tool ID | UI Label | Description |
|---------|----------|-------------|
| `general` | (none) | No tool selected — general chat |
| `image` | Bild erstellen | Create images with Imagen AI |
| `video` | Video erstellen | Create videos with Veo 2 |
| `canvas` | Canvas | Interactive workspace for docs, code, and visualizations |
| `deep_research` | Deep Research | Multi-step research with web search and source synthesis |
| `music` | Musik erstellen | Create music with AI |
| `learning` | Lernhilfe | Guided learning and tutoring assistance |
| `deep_think` | Deep Think | Extended reasoning mode (requires Ultra subscription) |

```batch
:: Use Canvas for code/doc creation
python main.py --prompt "build a markdown editor" --tool canvas

:: Deep Research for complex topics
python main.py --prompt "climate change impacts on agriculture" --tool deep_research --model pro

:: Image generation
python main.py --prompt "a cat wearing a hat, digital art" --tool image
```

If a tool is unavailable (disabled by plan/region), the pipeline logs a warning and continues in general mode.

---

## Tool Mode

Exposes the pipeline as a callable tool for AI agents. Returns structured JSON.

### Schema

```json
{
  "name": "gemini_web_chat",
  "description": "Automates interaction with Gemini web chat using Playwright.",
  "parameters": {
    "type": "object",
    "properties": {
      "prompt": {
        "type": "string",
        "description": "The prompt to send to Gemini"
      },
      "model": {
        "type": "string",
        "enum": ["fast", "thinking", "pro"],
        "description": "Gemini model mode (default: pro)"
      },
      "tool": {
        "type": "string",
        "enum": ["general", "image", "video", "canvas", "deep_research", "music", "learning", "deep_think"],
        "description": "Gemini tool to activate (default: general)"
      },
      "output_dir": {
        "type": "string",
        "description": "Output directory (default: ./output)"
      },
      "headless": {
        "type": "boolean",
        "description": "Run headless (default: true in tool mode)"
      },
      "timeout": {
        "type": "integer",
        "description": "Response timeout in seconds (default: 120)"
      }
    },
    "required": []
  }
}
```

### Usage from CLI

```batch
:: Get the JSON schema
python main.py --mode tool --schema

:: Execute a prompt as a tool
python main.py --mode tool --prompt "What is ML?" --json

:: With model selection
python main.py --mode tool --prompt "Solve x^2 + 2x + 1 = 0" --model thinking --json

:: With tool selection
python main.py --mode tool --prompt "design a dashboard" --tool canvas --json

:: Headless tool execution
python main.py --mode tool --prompt "research quantum computing" --tool deep_research --headless --json
```

### Example Response

```json
{
  "success": true,
  "prompt": "What is machine learning?",
  "response": "Machine learning is...",
  "thinking": "I need to explain ML...",
  "model": "Gemini Fast",
  "tool": "general",
  "tool_label": null,
  "duration": 15.32,
  "response_file": "output\\gemini_response_20260516_123456.json",
  "response_length": 1247,
  "tool": "gemini_web_chat"
}
```

### Integration with AI Agents

```python
from tool_mode import execute_tool

result = await execute_tool({
    "prompt": "Explain quantum computing",
    "model": "thinking",
    "headless": True
})
print(result["response"])
```

---

## MCP Server Mode

Model Context Protocol (MCP) server that exposes the Gemini pipeline as a tool for AI agent frameworks. Communicates via stdin/stdout using JSON-RPC.

### Starting the Server

```batch
python main.py --mode mcp
```

The server listens on stdin for JSON-RPC messages and responds on stdout. Configure it as an MCP tool in your agent framework.

### Supported Methods

#### `initialize`

```json
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
```

Response includes server info and capabilities.

#### `tools/list`

```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
```

Returns the `gemini_web_chat` tool with its input schema.

#### `tools/call`

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "gemini_web_chat",
    "arguments": {
      "prompt": "Explain quantum computing",
      "model": "thinking",
      "tool": "deep_research",
      "headless": true
    }
  }
}
```

Response contains the full result with thinking, answer, and metadata.

#### `ping`

```json
{"jsonrpc": "2.0", "id": 4, "method": "ping", "params": {}}
```

### Integration Example (Claude Desktop / Cline)

Add to your MCP settings:

```json
{
  "mcpServers": {
    "gemini-web-chat": {
      "command": "python",
      "args": ["main.py", "--mode", "mcp"]
    }
  }
}
```

---

## Output Format

Every run produces a single JSON file in the output directory:

```json
{
  "timestamp": "2026-05-16T09:51:29.134119",
  "prompt": "What is the difference between TCP and UDP?",
  "thinking": "Defining the comparison parameters...",
  "answer": "At a high level, the difference between TCP and UDP...",
  "model": "Gemini Thinking",
  "model_selected": "thinking",
  "tool": "general",
  "tool_label": null,
  "duration_seconds": 36.63,
  "duration_formatted": "0m 36s",
  "error": null,
  "response_length": 2624,
  "thinking_length": 126
}
```

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 timestamp of the run |
| `prompt` | The original prompt sent to Gemini |
| `thinking` | Gemini's thought process (if shown) |
| `answer` | The model's final response |
| `model` | Detected model name (e.g. Gemini Fast, Gemini Thinking) |
| `model_selected` | Requested model mode (`fast`, `thinking`, `pro`) |
| `tool` | Selected tool ID (`general`, `image`, `video`, `canvas`, `deep_research`, `music`, `learning`, `deep_think`) |
| `tool_label` | Human-readable tool name (e.g. "Canvas", "Deep Research") |
| `duration_seconds` | Total execution time in seconds |
| `duration_formatted` | Human-readable duration |
| `error` | Error message if failed, null otherwise |
| `response_length` | Character count of the answer |
| `thinking_length` | Character count of the thinking section |

---

## File Structure

```
project/
├── gemini_pipeline.py    # Core pipeline class (models + tools)
├── main.py               # Entry point with mode selection
├── tool_mode.py          # AI agent tool interface with tool schema
├── mcp_server.py         # MCP server implementation with tool support
├── run_pipeline.bat      # Windows runner with venv auto-setup
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── output/
    ├── gemini_session.json        # Saved login session
    ├── gemini_response_*.json     # Response outputs (includes tool info)
    └── error_screenshot.png       # Debug screenshot on errors
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Login required every time** | Run once with `--persistent` to save session, or check `output/gemini_session.json` exists |
| **Browser doesn't start** | Ensure Chrome is installed. The pipeline uses `channel='chrome'` |
| **"I/O operation on closed file"** | Use `python -u` flag for unbuffered output |
| **Timeout** | Increase `--timeout` (e.g., `--timeout 300`). Complex thinking responses take longer |
| **No response detected** | The `Waiting for response...` message appears — check URL printed. If not `gemini.google.com/app`, session may be expired |
| **Tool shows as disabled** | Tool availability depends on your Google account plan. The pipeline detects and warns if a tool is disabled. Use `--tool general` to skip tool selection |
| **Unicode errors in console** | Fixed by `sys.stdout.reconfigure(encoding='utf-8')` in the pipeline |
| **Thinking section empty** | Gemini doesn't show thinking for all queries. Only complex reasoning prompts trigger it |

> **Note**: This tool automates a web interface. Use responsibly and in accordance with Google's Terms of Service for Gemini.
