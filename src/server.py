"""
Poke Dispatch MCP Server.

FastMCP server exposing 40+ tools for Claude Code orchestration,
file management, web access, AI utilities, and system monitoring.

Runs locally on port 8000 or on Render.com via the PORT env var.
In Render mode, local-only tools (sessions, clipboard, notifications)
return a helpful message directing users to poke tunnel.
"""

import os

from fastmcp import FastMCP

from src.config import MCP_PATH, SERVER_HOST

# Import all tool modules
from src.tools import (
    ai,
    comms,
    files,
    monitor,
    notes,
    schedule,
    sessions,
    system,
    tasks,
    web,
)

mcp = FastMCP(
    name="Poke Dispatch",
    instructions=(
        "Poke Dispatch is a full orchestration MCP server. "
        "Use it to manage Claude Code sessions, plan and route tasks, "
        "read/write files, search the web, schedule jobs, store notes, "
        "monitor system health, and run AI-powered code analysis. "
        "In local mode all tools are available. "
        "In Render mode, session/clipboard/notification tools are disabled."
    ),
)

# ---- Session Management ----
mcp.tool(sessions.start_session)
mcp.tool(sessions.send_to_session)
mcp.tool(sessions.list_sessions)
mcp.tool(sessions.read_session)
mcp.tool(sessions.stop_session)
mcp.tool(sessions.resume_session)

# ---- Task Planning and Routing ----
mcp.tool(tasks.plan_task)
mcp.tool(tasks.route_task)
mcp.tool(tasks.batch_tasks)

# ---- File Operations ----
mcp.tool(files.list_files)
mcp.tool(files.read_file)
mcp.tool(files.write_file)
mcp.tool(files.search_files)
mcp.tool(files.search_code)
mcp.tool(files.git_status)
mcp.tool(files.git_log)

# ---- System Tools ----
mcp.tool(system.run_command)
mcp.tool(system.get_system_info)
mcp.tool(system.list_processes)
mcp.tool(system.kill_process)

# ---- Web Tools ----
mcp.tool(web.web_search)
mcp.tool(web.fetch_url)
mcp.tool(web.summarize_url)

# ---- Scheduling ----
mcp.tool(schedule.schedule_task)
mcp.tool(schedule.list_schedules)
mcp.tool(schedule.remove_schedule)
mcp.tool(schedule.run_scheduled_now)

# ---- Notes and Memory ----
mcp.tool(notes.save_note)
mcp.tool(notes.list_notes)
mcp.tool(notes.read_note)
mcp.tool(notes.search_notes)
mcp.tool(notes.save_context)
mcp.tool(notes.get_context)
mcp.tool(notes.list_context)

# ---- Monitoring ----
mcp.tool(monitor.check_health)
mcp.tool(monitor.get_dashboard)
mcp.tool(monitor.get_activity_log)

# ---- Communications ----
mcp.tool(comms.send_notification)
mcp.tool(comms.clipboard_read)
mcp.tool(comms.clipboard_write)

# ---- AI Utilities ----
mcp.tool(ai.ask_claude)
mcp.tool(ai.analyze_file)
mcp.tool(ai.generate_code)
mcp.tool(ai.review_code)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="sse", host=SERVER_HOST, port=port, path=MCP_PATH)
