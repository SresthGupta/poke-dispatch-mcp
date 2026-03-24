"""
System-level tools for shell execution and process management.

All shell commands are filtered against a blocklist of dangerous patterns
before execution to prevent accidental destructive operations.
"""

import os
import subprocess
import time
from typing import Optional

import psutil

from src import db
from src.config import (
    BLOCKED_COMMANDS,
    BLOCKED_PREFIXES,
    DEFAULT_COMMAND_TIMEOUT,
    MAX_COMMAND_TIMEOUT,
    DEPLOY_MODE,
)

LOCAL_ONLY_MSG = "This tool is only available in local mode. Run with poke tunnel for full access."


def _is_blocked(command: str) -> bool:
    """Return True if the command matches any blocked pattern."""
    cmd_lower = command.lower().strip()
    for blocked in BLOCKED_COMMANDS:
        if blocked in cmd_lower:
            return True
    for prefix in BLOCKED_PREFIXES:
        if cmd_lower.startswith(prefix):
            return True
    return False


def run_command(command: str, timeout: Optional[int] = None, cwd: Optional[str] = None) -> dict:
    """
    Execute a shell command safely with a blocklist check.

    Dangerous commands (rm -rf /, sudo, etc.) are rejected before execution.

    Args:
        command: Shell command string to execute.
        timeout: Seconds to wait before killing the process. Max 300.
        cwd:     Working directory for the command.

    Returns:
        dict with stdout, stderr, return_code, and duration.
    """
    start = time.time()
    if DEPLOY_MODE == "render":
        result = {"error": LOCAL_ONLY_MSG}
        db.log_tool_call("run_command", {"command": command}, result, success=False)
        return result

    if _is_blocked(command):
        result = {"error": f"Command blocked for safety: '{command[:80]}'"}
        db.log_tool_call("run_command", {"command": command}, result, success=False)
        return result

    actual_timeout = min(timeout or DEFAULT_COMMAND_TIMEOUT, MAX_COMMAND_TIMEOUT)
    resolved_cwd = os.path.expanduser(cwd) if cwd else None

    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=actual_timeout,
            cwd=resolved_cwd,
        )
        duration_ms = int((time.time() - start) * 1000)
        result = {
            "stdout": proc.stdout[:5000],
            "stderr": proc.stderr[:2000],
            "return_code": proc.returncode,
            "success": proc.returncode == 0,
            "duration_ms": duration_ms,
            "command": command,
        }
        db.log_tool_call("run_command", {"command": command, "timeout": actual_timeout}, result, duration_ms=duration_ms)
        return result
    except subprocess.TimeoutExpired:
        result = {"error": f"Command timed out after {actual_timeout}s.", "command": command}
        db.log_tool_call("run_command", {"command": command}, result, success=False)
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("run_command", {"command": command}, result, success=False)
        return result


def get_system_info() -> dict:
    """
    Return current system resource information.

    Includes CPU usage, memory usage, disk usage, and platform details.

    Returns:
        dict with cpu_percent, memory, disk, and platform info.
    """
    start = time.time()
    try:
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        result = {
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "cpu_count": psutil.cpu_count(),
            "memory": {
                "total_gb": round(mem.total / 1e9, 2),
                "used_gb": round(mem.used / 1e9, 2),
                "available_gb": round(mem.available / 1e9, 2),
                "percent": mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / 1e9, 2),
                "used_gb": round(disk.used / 1e9, 2),
                "free_gb": round(disk.free / 1e9, 2),
                "percent": disk.percent,
            },
            "platform": {
                "system": os.uname().sysname,
                "node": os.uname().nodename,
                "release": os.uname().release,
            },
        }
        db.log_tool_call("get_system_info", {}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("get_system_info", {}, result, success=False)
        return result


def list_processes() -> dict:
    """
    List all currently running processes with resource usage.

    Returns:
        dict with list of processes sorted by CPU usage descending.
    """
    start = time.time()
    procs = []
    for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status", "username"]):
        try:
            info = proc.info
            procs.append({
                "pid": info["pid"],
                "name": info["name"],
                "cpu_percent": round(info["cpu_percent"] or 0, 2),
                "memory_percent": round(info["memory_percent"] or 0, 2),
                "status": info["status"],
                "user": info["username"],
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
    result = {"processes": procs[:50], "total": len(procs)}
    db.log_tool_call("list_processes", {}, {"total": len(procs)}, duration_ms=int((time.time()-start)*1000))
    return result


def kill_process(pid: int) -> dict:
    """
    Send SIGTERM to a process by PID, then SIGKILL if it does not exit.

    Args:
        pid: Process ID to terminate.

    Returns:
        dict with success status.
    """
    start = time.time()
    if DEPLOY_MODE == "render":
        result = {"error": LOCAL_ONLY_MSG}
        db.log_tool_call("kill_process", {"pid": pid}, result, success=False)
        return result

    try:
        proc = psutil.Process(pid)
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except psutil.TimeoutExpired:
            proc.kill()
        result = {"success": True, "pid": pid, "action": "terminated"}
        db.log_tool_call("kill_process", {"pid": pid}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except psutil.NoSuchProcess:
        result = {"error": f"No process with PID {pid}"}
        db.log_tool_call("kill_process", {"pid": pid}, result, success=False)
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("kill_process", {"pid": pid}, result, success=False)
        return result
