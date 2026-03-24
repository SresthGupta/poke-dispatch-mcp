# Poke Dispatch MCP

A thin Claude Code CLI wrapper that gives [Poke](https://poke.com) (by Interaction Co.) the ability to run Claude Code on your Mac. Claude Code itself handles file access, web search, code execution, and everything else - this MCP just bridges Poke to Claude Code.

## Tools

| Tool | Description |
|---|---|
| `run_task` | Run a quick task synchronously (blocks up to 5 min) |
| `start_task` | Start a longer task in the background, returns session_id |
| `check_task` | Check status and output of a background task |
| `send_followup` | Send a follow-up message to a running task |
| `run_parallel` | Spawn multiple Claude Code tasks simultaneously |
| `list_tasks` | List all tracked tasks |

## Requirements

- Python 3.11+
- Claude Code CLI installed (`npm install -g @anthropic-ai/claude-code`)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/SresthGupta/poke-dispatch-mcp.git
cd poke-dispatch-mcp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start the server

```bash
python -m src.server
# Server starts at http://localhost:8000/mcp
```

### 3. Create a poke tunnel

```bash
npm install -g poke
poke tunnel http://localhost:8000/mcp --name "Dispatch"
```

Paste the tunnel URL into Poke under **Settings > MCP Servers**.

## Render Deployment

Deploy to [Render.com](https://render.com) using the included `render.yaml`. The Claude Code CLI must be available in the environment.

- Build command: `pip install -r requirements.txt`
- Start command: `python -m src.server`

## Development

```bash
# Test Claude Code CLI works
claude --print "hello"

# Start server
python -m src.server

# List registered tools
python -c "from src.server import mcp; print([t for t in mcp._tool_manager._tools])"
```
