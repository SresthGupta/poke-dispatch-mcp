import os
import time

from fastmcp import FastMCP
import sys; sys.path.insert(0, os.path.dirname(__file__)); from claude import ClaudeManager

mcp = FastMCP(
    "Poke Dispatch",
    instructions="Poke Dispatch is a Claude Code wrapper. Use run_task for quick tasks, start_task for longer work, check_task to monitor, send_followup to interact with running tasks, run_parallel to spawn multiple tasks at once, list_tasks to see all."
)
manager = ClaudeManager()


@mcp.tool(description="Run a quick task with Claude Code and get the result. Blocks until done (up to 5 min). Good for simple questions, file reads, quick code changes.")
def run_task(prompt: str, working_directory: str = "~/Agents") -> str:
    return manager.run_sync(prompt, working_directory)


@mcp.tool(description="Start a longer Claude Code task in the background. Returns a session_id to track progress. Use check_task to monitor.")
def start_task(prompt: str, working_directory: str = "~/Agents") -> str:
    sid = manager.start_async(prompt, working_directory)
    return f"Started task {sid}. Use check_task('{sid}') to monitor progress."


@mcp.tool(description="Check status and latest output of a background task.")
def check_task(session_id: str) -> str:
    session = manager.get_session(session_id)
    if not session:
        return f"No task found with id {session_id}"
    duration = (session.end_time or time.time()) - session.start_time
    output = session.get_text_result()
    return f"Status: {session.status}\nDuration: {duration:.0f}s\nPrompt: {session.prompt[:100]}\n\nOutput:\n{output}"


@mcp.tool(description="Send a follow-up message to a running background task.")
def send_followup(session_id: str, message: str) -> str:
    session = manager.get_session(session_id)
    if not session:
        return f"No task found with id {session_id}"
    if session.send_message(message):
        return "Follow-up sent"
    return "Task is no longer running"


@mcp.tool(description="Run multiple Claude Code tasks in parallel simultaneously. Takes a list of prompt strings and spawns them all at once. Returns all session IDs so you can check_task on each one.")
def run_parallel(tasks: list[str], working_directory: str = "~/Agents") -> str:
    if not tasks:
        return "No tasks provided"
    session_ids = manager.start_parallel(tasks, working_directory)
    lines = [f"Started {len(session_ids)} parallel tasks:"]
    for sid in session_ids:
        lines.append(f"  {sid}")
    lines.append("Use check_task('<session_id>') to monitor each one.")
    return "\n".join(lines)


@mcp.tool(description="List all tracked tasks (running and recent completed).")
def list_tasks() -> str:
    sessions = manager.list_all()
    if not sessions:
        return "No tasks tracked yet"
    lines = []
    for s in sessions[-10:]:
        dur = (s.end_time or time.time()) - s.start_time
        lines.append(f"[{s.session_id}] {s.status} ({dur:.0f}s) - {s.prompt[:80]}")
    return "\n".join(lines)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port, path="/mcp")
