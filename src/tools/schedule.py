"""
Task scheduling tools using macOS launchd plist files.

Create, list, remove, and immediately run scheduled tasks.
Each scheduled task is a launchd agent that runs a shell command on a cron schedule.
"""

import os
import plistlib
import subprocess
import time
from pathlib import Path
from typing import Optional

from src import db

LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PREFIX = "com.poke.dispatch."


def _plist_path(name: str) -> Path:
    safe_name = name.replace(" ", "_").replace("/", "_")
    return LAUNCH_AGENTS_DIR / f"{PLIST_PREFIX}{safe_name}.plist"


def schedule_task(task: str, cron: str, name: str) -> dict:
    """
    Create a launchd scheduled task that runs on a cron-style schedule.

    Creates a plist file in ~/Library/LaunchAgents and loads it with launchctl.

    Args:
        task: Shell command to execute on schedule.
        cron: Cron expression (e.g. '0 9 * * 1' for Monday 9am).
              Supports: minute hour day-of-month month day-of-week.
        name: Unique name for this scheduled task.

    Returns:
        dict with plist path and success status.
    """
    start = time.time()
    if not name or not task or not cron:
        result = {"error": "name, task, and cron are all required."}
        db.log_tool_call("schedule_task", {"name": name, "task": task, "cron": cron}, result, success=False)
        return result

    # Parse cron into launchd StartCalendarInterval
    try:
        parts = cron.strip().split()
        if len(parts) != 5:
            raise ValueError("Cron must have 5 fields: minute hour day month weekday")
        minute, hour, dom, month, dow = parts
        calendar = {}
        if minute != "*":
            calendar["Minute"] = int(minute)
        if hour != "*":
            calendar["Hour"] = int(hour)
        if dom != "*":
            calendar["Day"] = int(dom)
        if month != "*":
            calendar["Month"] = int(month)
        if dow != "*":
            calendar["Weekday"] = int(dow)
    except ValueError as e:
        result = {"error": f"Invalid cron expression: {e}"}
        db.log_tool_call("schedule_task", {"name": name, "task": task, "cron": cron}, result, success=False)
        return result

    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    plist_path = _plist_path(name)
    label = f"{PLIST_PREFIX}{name.replace(' ', '_')}"

    plist_data = {
        "Label": label,
        "ProgramArguments": ["/bin/sh", "-c", task],
        "StartCalendarInterval": calendar,
        "RunAtLoad": False,
        "StandardOutPath": str(Path.home() / f".poke_schedule_{name}.log"),
        "StandardErrorPath": str(Path.home() / f".poke_schedule_{name}.err"),
    }

    try:
        with open(plist_path, "wb") as f:
            plistlib.dump(plist_data, f)
        subprocess.run(["launchctl", "load", str(plist_path)], check=True, capture_output=True)
        result = {
            "success": True,
            "name": name,
            "plist": str(plist_path),
            "label": label,
            "cron": cron,
            "task": task,
        }
        db.log_tool_call("schedule_task", {"name": name, "task": task, "cron": cron}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except subprocess.CalledProcessError as e:
        result = {"error": f"launchctl error: {e.stderr.decode() if e.stderr else str(e)}"}
        db.log_tool_call("schedule_task", {"name": name}, result, success=False)
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("schedule_task", {"name": name}, result, success=False)
        return result


def list_schedules() -> dict:
    """
    List all Poke Dispatch scheduled tasks.

    Returns:
        dict with list of scheduled task names and their plist paths.
    """
    start = time.time()
    schedules = []
    if LAUNCH_AGENTS_DIR.exists():
        for plist_path in LAUNCH_AGENTS_DIR.glob(f"{PLIST_PREFIX}*.plist"):
            name = plist_path.stem.replace(PLIST_PREFIX, "")
            try:
                with open(plist_path, "rb") as f:
                    data = plistlib.load(f)
                schedules.append({
                    "name": name,
                    "label": data.get("Label", ""),
                    "command": " ".join(data.get("ProgramArguments", [])),
                    "schedule": data.get("StartCalendarInterval", {}),
                    "plist": str(plist_path),
                })
            except Exception:
                schedules.append({"name": name, "plist": str(plist_path), "error": "Could not parse plist"})

    result = {"schedules": schedules, "count": len(schedules)}
    db.log_tool_call("list_schedules", {}, result, duration_ms=int((time.time()-start)*1000))
    return result


def remove_schedule(name: str) -> dict:
    """
    Unload and delete a scheduled task by name.

    Args:
        name: Name of the scheduled task to remove.

    Returns:
        dict with success status.
    """
    start = time.time()
    plist_path = _plist_path(name)
    if not plist_path.exists():
        result = {"error": f"No schedule found with name: {name}"}
        db.log_tool_call("remove_schedule", {"name": name}, result, success=False)
        return result
    try:
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        plist_path.unlink()
        result = {"success": True, "name": name, "removed": str(plist_path)}
        db.log_tool_call("remove_schedule", {"name": name}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("remove_schedule", {"name": name}, result, success=False)
        return result


def run_scheduled_now(name: str) -> dict:
    """
    Immediately trigger a scheduled task without waiting for its schedule.

    Args:
        name: Name of the scheduled task to run now.

    Returns:
        dict with success status.
    """
    start = time.time()
    plist_path = _plist_path(name)
    if not plist_path.exists():
        result = {"error": f"No schedule found with name: {name}"}
        db.log_tool_call("run_scheduled_now", {"name": name}, result, success=False)
        return result
    try:
        with open(plist_path, "rb") as f:
            data = plistlib.load(f)
        label = data.get("Label", "")
        proc = subprocess.run(
            ["launchctl", "start", label],
            capture_output=True, text=True
        )
        result = {
            "success": proc.returncode == 0,
            "name": name,
            "label": label,
            "stderr": proc.stderr,
        }
        db.log_tool_call("run_scheduled_now", {"name": name}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("run_scheduled_now", {"name": name}, result, success=False)
        return result
