"""
Claude Code session management tools.

Spawn, communicate with, monitor, and stop Claude Code subprocess sessions.
Each session runs a `claude` CLI process that can execute tasks autonomously.
"""

import os
import subprocess
import time
import uuid
from typing import Optional

from src import db
from src.config import DEPLOY_MODE, MAX_SESSIONS

LOCAL_ONLY_MSG = "This tool is only available in local mode. Run with poke tunnel for full access."


# In-memory store of live subprocess handles
_processes: dict[str, subprocess.Popen] = {}
_output_buffers: dict[str, list[str]] = {}


def start_session(task: str, cwd: str = ".") -> dict:
    """
    Spawn a new Claude Code CLI session for the given task.

    Starts `claude --print` as a subprocess, assigns it a session_id,
    and tracks it in both memory and the database.

    Args:
        task: Description of the task for Claude to work on.
        cwd:  Working directory for the Claude session. Defaults to current dir.

    Returns:
        dict with session_id, pid, task, status.
    """
    start = time.time()
    if DEPLOY_MODE == "render":
        result = {"error": LOCAL_ONLY_MSG}
        db.log_tool_call("start_session", {"task": task, "cwd": cwd}, result, success=False)
        return result
    active = [s for s in db.get_all_sessions() if s["status"] == "running"]
    if len(active) >= MAX_SESSIONS:
        result = {"error": f"Max sessions ({MAX_SESSIONS}) reached. Stop one first."}
        db.log_tool_call("start_session", {"task": task, "cwd": cwd}, result, success=False)
        return result

    session_id = str(uuid.uuid4())[:8]
    resolved_cwd = os.path.expanduser(cwd)
    if not os.path.isdir(resolved_cwd):
        result = {"error": f"Directory not found: {resolved_cwd}"}
        db.log_tool_call("start_session", {"task": task, "cwd": cwd}, result, success=False)
        return result

    try:
        proc = subprocess.Popen(
            ["claude", "--print", task],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=resolved_cwd,
            text=True,
            bufsize=1,
        )
        _processes[session_id] = proc
        _output_buffers[session_id] = []
        db.upsert_session(session_id, task, resolved_cwd, proc.pid)
        result = {
            "session_id": session_id,
            "pid": proc.pid,
            "task": task,
            "cwd": resolved_cwd,
            "status": "running",
        }
        db.log_tool_call("start_session", {"task": task, "cwd": cwd}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except FileNotFoundError:
        result = {"error": "claude CLI not found. Install Claude Code first."}
        db.log_tool_call("start_session", {"task": task, "cwd": cwd}, result, success=False)
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("start_session", {"task": task, "cwd": cwd}, result, success=False)
        return result


def send_to_session(session_id: str, message: str) -> dict:
    """
    Send a follow-up message to a running Claude Code session via stdin.

    Args:
        session_id: The session ID returned by start_session.
        message:    Text message to send.

    Returns:
        dict with success status.
    """
    start = time.time()
    if DEPLOY_MODE == "render":
        result = {"error": LOCAL_ONLY_MSG}
        db.log_tool_call("send_to_session", {"session_id": session_id, "message": message}, result, success=False)
        return result
    proc = _processes.get(session_id)
    if not proc:
        result = {"error": f"Session {session_id} not found in memory. It may have ended."}
        db.log_tool_call("send_to_session", {"session_id": session_id, "message": message}, result, success=False)
        return result
    if proc.poll() is not None:
        db.update_session_status(session_id, "stopped")
        result = {"error": f"Session {session_id} process has exited."}
        db.log_tool_call("send_to_session", {"session_id": session_id, "message": message}, result, success=False)
        return result
    try:
        proc.stdin.write(message + "\n")
        proc.stdin.flush()
        result = {"success": True, "session_id": session_id, "message_sent": message}
        db.log_tool_call("send_to_session", {"session_id": session_id, "message": message}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("send_to_session", {"session_id": session_id, "message": message}, result, success=False)
        return result


def list_sessions() -> dict:
    """
    List all tracked Claude Code sessions with their current status.

    Returns:
        dict with list of sessions including session_id, task, pid, status, cwd.
    """
    start = time.time()
    sessions = db.get_all_sessions()
    # Sync in-memory process state back to DB
    for s in sessions:
        sid = s["session_id"]
        proc = _processes.get(sid)
        if proc and proc.poll() is not None and s["status"] == "running":
            db.update_session_status(sid, "stopped")
            s["status"] = "stopped"
    result = {"sessions": sessions, "total": len(sessions)}
    db.log_tool_call("list_sessions", {}, result, duration_ms=int((time.time()-start)*1000))
    return result


def read_session(session_id: str, lines: int = 50) -> dict:
    """
    Read the latest output lines from a Claude Code session.

    Reads available stdout from the subprocess non-blockingly.

    Args:
        session_id: The session ID to read from.
        lines:      Number of recent lines to return.

    Returns:
        dict with output text and line count.
    """
    start = time.time()
    proc = _processes.get(session_id)
    if not proc:
        # Try to get info from DB only
        session = db.get_session(session_id)
        if not session:
            result = {"error": f"Session {session_id} not found."}
            db.log_tool_call("read_session", {"session_id": session_id, "lines": lines}, result, success=False)
            return result
        result = {"session_id": session_id, "output": "[Session not in memory - may have ended]", "status": session["status"]}
        db.log_tool_call("read_session", {"session_id": session_id, "lines": lines}, result)
        return result

    # Read available output without blocking
    buf = _output_buffers.setdefault(session_id, [])
    if proc.stdout:
        import select
        while True:
            ready, _, _ = select.select([proc.stdout], [], [], 0)
            if not ready:
                break
            line = proc.stdout.readline()
            if not line:
                break
            buf.append(line.rstrip())

    recent = buf[-lines:] if len(buf) > lines else buf
    status = "running" if proc.poll() is None else "stopped"
    result = {
        "session_id": session_id,
        "status": status,
        "output": "\n".join(recent),
        "total_lines": len(buf),
    }
    db.log_tool_call("read_session", {"session_id": session_id, "lines": lines}, result, duration_ms=int((time.time()-start)*1000))
    return result


def stop_session(session_id: str) -> dict:
    """
    Kill a running Claude Code session process.

    Args:
        session_id: The session ID to stop.

    Returns:
        dict with success status.
    """
    start = time.time()
    if DEPLOY_MODE == "render":
        result = {"error": LOCAL_ONLY_MSG}
        db.log_tool_call("stop_session", {"session_id": session_id}, result, success=False)
        return result
    proc = _processes.get(session_id)
    if not proc:
        session = db.get_session(session_id)
        if not session:
            result = {"error": f"Session {session_id} not found."}
            db.log_tool_call("stop_session", {"session_id": session_id}, result, success=False)
            return result
        result = {"warning": "Session not in memory, may already be stopped.", "session_id": session_id}
        db.log_tool_call("stop_session", {"session_id": session_id}, result)
        return result
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    except Exception:
        pass
    finally:
        _processes.pop(session_id, None)
        db.update_session_status(session_id, "stopped")

    result = {"success": True, "session_id": session_id, "status": "stopped"}
    db.log_tool_call("stop_session", {"session_id": session_id}, result, duration_ms=int((time.time()-start)*1000))
    return result


def resume_session(session_id: str) -> dict:
    """
    Resume a stopped Claude Code session using the --resume flag.

    Looks up the original task and cwd from the database and spawns a new
    `claude --resume` subprocess under the same session_id.

    Args:
        session_id: The session ID to resume.

    Returns:
        dict with new pid and status.
    """
    start = time.time()
    if DEPLOY_MODE == "render":
        result = {"error": LOCAL_ONLY_MSG}
        db.log_tool_call("resume_session", {"session_id": session_id}, result, success=False)
        return result
    session = db.get_session(session_id)
    if not session:
        result = {"error": f"Session {session_id} not found in database."}
        db.log_tool_call("resume_session", {"session_id": session_id}, result, success=False)
        return result

    cwd = session.get("cwd", ".")
    task = session.get("task", "")
    try:
        proc = subprocess.Popen(
            ["claude", "--resume", "--print", task],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=cwd,
            text=True,
            bufsize=1,
        )
        _processes[session_id] = proc
        _output_buffers[session_id] = []
        db.upsert_session(session_id, task, cwd, proc.pid, status="running")
        result = {
            "session_id": session_id,
            "pid": proc.pid,
            "status": "running",
            "task": task,
            "cwd": cwd,
        }
        db.log_tool_call("resume_session", {"session_id": session_id}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("resume_session", {"session_id": session_id}, result, success=False)
        return result
