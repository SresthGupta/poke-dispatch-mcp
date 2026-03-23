import os
import platform
import subprocess
import shlex
from typing import Optional

import psutil


# Commands and patterns that are blocked for safety
BLOCKED_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    ":(){ :|:& };:",  # fork bomb
    "> /dev/sda",
    "dd if=/dev/zero",
    "mkfs",
    "fdisk",
    "format c:",
    "deltree",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
    "sudo rm",
    "sudo mkfs",
    "sudo dd",
]

BLOCKED_COMMANDS = {
    "rm",
    "mkfs",
    "fdisk",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init",
}

MAX_OUTPUT_CHARS = 10000


def run_command(command: str, timeout: int = 30) -> str:
    """Execute a shell command with safety restrictions."""
    if not command.strip():
        return "Error: command cannot be empty"

    # Check for blocked patterns
    cmd_lower = command.lower().strip()
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in cmd_lower:
            return f"Error: command blocked for safety reasons (matched pattern: '{pattern}')"

    # Check the base command
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return f"Error: could not parse command: {e}"

    if not parts:
        return "Error: command cannot be empty"

    base_cmd = os.path.basename(parts[0]).lower()
    if base_cmd in BLOCKED_COMMANDS:
        return f"Error: command '{base_cmd}' is blocked for safety reasons"

    # Block sudo escalation
    if parts[0] == "sudo" or "sudo " in command:
        return "Error: sudo commands are not allowed"

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n--- stderr ---\n"
            output += result.stderr

        if not output:
            if result.returncode == 0:
                return "Command completed with no output (exit code 0)"
            else:
                return f"Command failed with exit code {result.returncode} (no output)"

        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + f"\n\n[Output truncated at {MAX_OUTPUT_CHARS} characters]"

        if result.returncode != 0:
            output = f"[Exit code: {result.returncode}]\n" + output

        return output
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout} seconds"
    except Exception as e:
        return f"Error running command: {e}"


def get_system_info() -> str:
    """Get OS, disk, memory, and CPU information."""
    try:
        lines = ["System Information", "=" * 40, ""]

        # OS info
        lines.append(f"OS: {platform.system()} {platform.release()}")
        lines.append(f"Version: {platform.version()}")
        lines.append(f"Architecture: {platform.machine()}")
        lines.append(f"Hostname: {platform.node()}")
        lines.append(f"Python: {platform.python_version()}")
        lines.append("")

        # CPU
        cpu_count = psutil.cpu_count(logical=True)
        cpu_physical = psutil.cpu_count(logical=False)
        cpu_percent = psutil.cpu_percent(interval=0.5)
        lines.append(f"CPU Cores: {cpu_physical} physical, {cpu_count} logical")
        lines.append(f"CPU Usage: {cpu_percent:.1f}%")
        lines.append("")

        # Memory
        mem = psutil.virtual_memory()
        lines.append(f"Memory Total: {_fmt_bytes(mem.total)}")
        lines.append(f"Memory Used: {_fmt_bytes(mem.used)} ({mem.percent:.1f}%)")
        lines.append(f"Memory Available: {_fmt_bytes(mem.available)}")
        lines.append("")

        # Disk
        disk = psutil.disk_usage("/")
        lines.append(f"Disk Total: {_fmt_bytes(disk.total)}")
        lines.append(f"Disk Used: {_fmt_bytes(disk.used)} ({disk.percent:.1f}%)")
        lines.append(f"Disk Free: {_fmt_bytes(disk.free)}")
        lines.append("")

        # Load average (Unix only)
        if hasattr(os, "getloadavg"):
            load = os.getloadavg()
            lines.append(f"Load Average (1m/5m/15m): {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}")

        return "\n".join(lines)
    except Exception as e:
        return f"Error getting system info: {e}"


def _fmt_bytes(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
