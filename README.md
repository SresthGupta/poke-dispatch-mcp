# Poke Dispatch MCP

A full-orchestration MCP server that gives [Poke](https://poke.com) (by Interaction Co.) 40+ tools for Claude Code session management, file operations, web search, task planning, scheduling, notes, system monitoring, and AI-powered code analysis.

Supports two deployment modes:
- **Local mode** (via poke tunnel): All tools available including Claude Code sessions, clipboard, and notifications.
- **Render mode**: All stateless tools available; local-only tools return a clear message directing you to use poke tunnel.

---

## Tools

| Category | Tool | Local | Render |
|---|---|---|---|
| Sessions | `start_session` | Yes | No |
| Sessions | `send_to_session` | Yes | No |
| Sessions | `list_sessions` | Yes | Yes |
| Sessions | `read_session` | Yes | Yes |
| Sessions | `stop_session` | Yes | No |
| Sessions | `resume_session` | Yes | No |
| Tasks | `plan_task` | Yes | Yes |
| Tasks | `route_task` | Yes | Yes |
| Tasks | `batch_tasks` | Yes | Yes |
| Files | `list_files` | Yes | Yes |
| Files | `read_file` | Yes | Yes |
| Files | `write_file` | Yes | Yes |
| Files | `search_files` | Yes | Yes |
| Files | `search_code` | Yes | Yes |
| Files | `git_status` | Yes | Yes |
| Files | `git_log` | Yes | Yes |
| System | `run_command` | Yes | No |
| System | `get_system_info` | Yes | Yes |
| System | `list_processes` | Yes | Yes |
| System | `kill_process` | Yes | No |
| Web | `web_search` | Yes | Yes |
| Web | `fetch_url` | Yes | Yes |
| Web | `summarize_url` | Yes | Yes |
| Schedule | `schedule_task` | Yes | Yes |
| Schedule | `list_schedules` | Yes | Yes |
| Schedule | `remove_schedule` | Yes | Yes |
| Schedule | `run_scheduled_now` | Yes | Yes |
| Notes | `save_note` | Yes | Yes |
| Notes | `list_notes` | Yes | Yes |
| Notes | `read_note` | Yes | Yes |
| Notes | `search_notes` | Yes | Yes |
| Notes | `save_context` | Yes | Yes |
| Notes | `get_context` | Yes | Yes |
| Notes | `list_context` | Yes | Yes |
| Monitor | `check_health` | Yes | Yes |
| Monitor | `get_dashboard` | Yes | Yes |
| Monitor | `get_activity_log` | Yes | Yes |
| Comms | `send_notification` | Yes | No |
| Comms | `clipboard_read` | Yes | No |
| Comms | `clipboard_write` | Yes | No |
| AI | `ask_claude` | Yes | Yes |
| AI | `analyze_file` | Yes | Yes |
| AI | `generate_code` | Yes | Yes |
| AI | `review_code` | Yes | Yes |

---

## Option A: Local Mode (poke tunnel)

Full access to all 40+ tools including Claude Code sessions, shell execution, clipboard, and macOS notifications.

### 1. Clone and install

```bash
git clone https://github.com/SresthGupta/poke-dispatch-mcp.git
cd poke-dispatch-mcp
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
```

### 3. Start the server

```bash
python src/server.py
# Server starts at http://localhost:8000/mcp
```

### 4. Create a poke tunnel

```bash
npm install -g poke
poke tunnel http://localhost:8000/mcp --name "Dispatch"
```

Paste the tunnel URL into Poke under **Settings > MCP Servers**.

---

## Option B: Render Deployment

Deploy to [Render.com](https://render.com) for a persistent cloud-hosted MCP server.
Session/clipboard/notification tools are disabled in this mode.

### 1. Deploy via Blueprint

Click "New Blueprint" in Render and point it at this repo. The `render.yaml` file configures everything automatically.

Or deploy manually:
- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `python src/server.py`
- Environment variables:
  - `ANTHROPIC_API_KEY`: your API key
  - `RENDER`: `true` (auto-set by Render)

### 2. Connect to Poke

Once deployed, copy your Render service URL (e.g. `https://poke-dispatch-mcp.onrender.com`) and add `/mcp` to get the endpoint:

```
https://poke-dispatch-mcp.onrender.com/mcp
```

Paste this into Poke under **Settings > MCP Servers**.

### 3. Upgrade to local when needed

For tools requiring local access (sessions, clipboard, shell commands), run the server locally with poke tunnel as described in Option A.

---

## Safety Restrictions

`run_command` blocks dangerous commands:
- `rm -rf /` and similar destructive patterns
- `sudo` and `su` escalation
- `shutdown`, `reboot`, `halt`
- `mkfs` and disk formatting tools
- Fork bombs and other destructive patterns

All tool calls are logged to SQLite at `data/poke_dispatch.db`.

## Development

```bash
# Run locally with auto-reload
python src/server.py

# Test the MCP endpoint
curl http://localhost:8000/mcp

# Verify all tools load
python -c "from src.server import mcp; print('Tools:', len(mcp._tool_manager._tools))"
```
