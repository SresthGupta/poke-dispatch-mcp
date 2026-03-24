"""
Communication tools for macOS notifications and clipboard access.

These tools are local-only and will return an informative error when
running in Render deploy mode.
"""

import subprocess
import time

from src import db
from src.config import DEPLOY_MODE

LOCAL_ONLY_MSG = "This tool is only available in local mode. Run with poke tunnel for full access."


def send_notification(title: str, message: str) -> dict:
    """
    Send a macOS system notification via osascript.

    Args:
        title:   Notification title shown in bold.
        message: Notification body text.

    Returns:
        dict with success status.
    """
    start = time.time()
    if DEPLOY_MODE == "render":
        result = {"error": LOCAL_ONLY_MSG}
        db.log_tool_call("send_notification", {"title": title, "message": message}, result, success=False)
        return result

    # Escape quotes to prevent AppleScript injection
    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=10)
        result = {"success": True, "title": title, "message": message}
        db.log_tool_call("send_notification", {"title": title, "message": message}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except subprocess.CalledProcessError as e:
        result = {"error": f"osascript failed: {e.stderr.decode() if e.stderr else str(e)}"}
        db.log_tool_call("send_notification", {"title": title, "message": message}, result, success=False)
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("send_notification", {"title": title, "message": message}, result, success=False)
        return result


def clipboard_read() -> dict:
    """
    Read the current macOS clipboard contents.

    Returns:
        dict with clipboard text content.
    """
    start = time.time()
    if DEPLOY_MODE == "render":
        result = {"error": LOCAL_ONLY_MSG}
        db.log_tool_call("clipboard_read", {}, result, success=False)
        return result

    try:
        proc = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5)
        content = proc.stdout
        result = {"content": content, "length": len(content)}
        db.log_tool_call("clipboard_read", {}, {"length": len(content)}, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("clipboard_read", {}, result, success=False)
        return result


def clipboard_write(text: str) -> dict:
    """
    Write text to the macOS clipboard.

    Args:
        text: Text content to place on the clipboard.

    Returns:
        dict with success status and character count.
    """
    start = time.time()
    if DEPLOY_MODE == "render":
        result = {"error": LOCAL_ONLY_MSG}
        db.log_tool_call("clipboard_write", {"text": text[:50]}, result, success=False)
        return result

    try:
        proc = subprocess.run(
            ["pbcopy"],
            input=text,
            text=True,
            capture_output=True,
            timeout=5,
        )
        if proc.returncode != 0:
            result = {"error": f"pbcopy failed: {proc.stderr}"}
            db.log_tool_call("clipboard_write", {}, result, success=False)
            return result
        result = {"success": True, "characters_written": len(text)}
        db.log_tool_call("clipboard_write", {"length": len(text)}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("clipboard_write", {}, result, success=False)
        return result
