# Poke Dispatch MCP

A locally hosted MCP server that gives [Poke](https://poke.com) (by Interaction Co.) access to Dispatch/Cowork-like tools: file management, web search, shell commands, notes, and clipboard access.

## Tools

| Category | Tool | Description |
|---|---|---|
| Files | `tool_list_files` | List directory contents |
| Files | `tool_read_file` | Read a file |
| Files | `tool_write_file` | Write/create a file |
| Files | `tool_search_files` | Find files by name pattern |
| Files | `tool_search_content` | Grep-like content search |
| Web | `tool_web_search` | Search the web via DuckDuckGo |
| Web | `tool_fetch_url` | Fetch and extract text from a URL |
| System | `tool_run_command` | Run shell commands (with safety restrictions) |
| System | `tool_get_system_info` | Get OS, CPU, memory, disk info |
| Notes | `tool_create_note` | Save a markdown note |
| Notes | `tool_list_notes` | List all saved notes |
| Notes | `tool_read_note` | Read a specific note |
| Clipboard | `tool_get_clipboard` | Read the clipboard |
| Clipboard | `tool_set_clipboard` | Write to the clipboard |

## Requirements

- Python 3.12+
- Node.js 18+ (for the poke tunnel)

## Setup

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/poke-dispatch-mcp.git
cd poke-dispatch-mcp

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` to set your workspace directory and port:

```
PORT=8000
WORKSPACE_DIR=~/poke-workspace
NOTES_DIR=~/poke-workspace/notes
```

### 3. Start the server

```bash
cd src
python server.py
```

You should see:

```
Starting Poke Dispatch MCP server on port 8000
Workspace: ~/poke-workspace
MCP endpoint: http://localhost:8000/mcp
```

### 4. Create a poke tunnel

In a new terminal:

```bash
npm install -g poke
poke tunnel http://localhost:8000/mcp --name "Dispatch"
```

The tunnel URL will be printed. Paste it into the Poke app under **Settings > MCP Servers**.

Tools sync automatically every 5 minutes. Press `Ctrl+C` to stop the tunnel.

## File Operations

All file operations are sandboxed to the workspace directory (default `~/poke-workspace`). Paths outside the workspace are blocked. The workspace directory is created automatically on first use.

## Safety Restrictions

`tool_run_command` blocks dangerous commands including:

- `rm -rf /` and similar destructive patterns
- `sudo` escalation
- `shutdown`, `reboot`, `halt`
- `mkfs`, `fdisk`, and disk formatting tools
- Fork bombs

## Development

```bash
# Run with auto-reload (requires fastmcp dev tools)
cd src
python server.py

# Test the MCP endpoint
curl http://localhost:8000/mcp
```
