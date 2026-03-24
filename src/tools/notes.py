"""
Notes and persistent memory tools.

Save and retrieve markdown notes as files in data/notes/.
Store arbitrary key/value context in SQLite for cross-session memory.
"""

import os
import time
from pathlib import Path
from typing import Any, Optional

from src import db
from src.config import NOTES_DIR


def _note_path(title: str) -> Path:
    safe = title.lower().replace(" ", "_").replace("/", "_").replace("..", "")
    return NOTES_DIR / f"{safe}.md"


def save_note(title: str, content: str) -> dict:
    """
    Save a markdown note to disk under data/notes/.

    Creates or overwrites a file named after the title.

    Args:
        title:   Note title (used as filename).
        content: Markdown content to save.

    Returns:
        dict with success status and file path.
    """
    start = time.time()
    if not title.strip():
        result = {"error": "Note title cannot be empty."}
        db.log_tool_call("save_note", {"title": title}, result, success=False)
        return result

    path = _note_path(title)
    try:
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n{content}")
        result = {"success": True, "title": title, "path": str(path)}
        db.log_tool_call("save_note", {"title": title}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("save_note", {"title": title}, result, success=False)
        return result


def list_notes() -> dict:
    """
    List all saved notes with their titles and modification times.

    Returns:
        dict with list of notes.
    """
    start = time.time()
    notes = []
    if NOTES_DIR.exists():
        for path in sorted(NOTES_DIR.glob("*.md")):
            stat = path.stat()
            notes.append({
                "title": path.stem.replace("_", " "),
                "file": path.name,
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
            })
    result = {"notes": notes, "count": len(notes)}
    db.log_tool_call("list_notes", {}, result, duration_ms=int((time.time()-start)*1000))
    return result


def read_note(title: str) -> dict:
    """
    Read the contents of a saved note by title.

    Args:
        title: Note title to look up.

    Returns:
        dict with note content and path.
    """
    start = time.time()
    path = _note_path(title)
    if not path.exists():
        result = {"error": f"Note not found: '{title}'"}
        db.log_tool_call("read_note", {"title": title}, result, success=False)
        return result
    try:
        content = path.read_text(encoding="utf-8")
        result = {"title": title, "content": content, "path": str(path)}
        db.log_tool_call("read_note", {"title": title}, {"chars": len(content)}, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("read_note", {"title": title}, result, success=False)
        return result


def search_notes(query: str) -> dict:
    """
    Search note contents for a query string.

    Args:
        query: Text to search for across all note files.

    Returns:
        dict with matching notes and the lines where the query appears.
    """
    start = time.time()
    if not query.strip():
        result = {"error": "Search query cannot be empty."}
        db.log_tool_call("search_notes", {"query": query}, result, success=False)
        return result

    matches = []
    if NOTES_DIR.exists():
        for path in NOTES_DIR.glob("*.md"):
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
                hits = [
                    {"line_num": i + 1, "line": line.strip()}
                    for i, line in enumerate(lines)
                    if query.lower() in line.lower()
                ]
                if hits:
                    matches.append({
                        "title": path.stem.replace("_", " "),
                        "file": path.name,
                        "hits": hits,
                    })
            except Exception:
                continue

    result = {"query": query, "matches": matches, "count": len(matches)}
    db.log_tool_call("search_notes", {"query": query}, {"count": len(matches)}, duration_ms=int((time.time()-start)*1000))
    return result


def save_context(key: str, value: Any) -> dict:
    """
    Persist a key/value pair in the SQLite context store.

    Useful for storing state or preferences across sessions.

    Args:
        key:   Unique key string.
        value: Any JSON-serializable value.

    Returns:
        dict with success status.
    """
    start = time.time()
    if not key.strip():
        result = {"error": "Context key cannot be empty."}
        db.log_tool_call("save_context", {"key": key}, result, success=False)
        return result
    try:
        db.set_context(key, value)
        result = {"success": True, "key": key}
        db.log_tool_call("save_context", {"key": key}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("save_context", {"key": key}, result, success=False)
        return result


def get_context(key: str) -> dict:
    """
    Retrieve a stored context value by key.

    Args:
        key: The key to look up.

    Returns:
        dict with key and value, or error if not found.
    """
    start = time.time()
    value = db.get_context(key)
    if value is None:
        result = {"error": f"No context found for key: '{key}'"}
        db.log_tool_call("get_context", {"key": key}, result, success=False)
        return result
    result = {"key": key, "value": value}
    db.log_tool_call("get_context", {"key": key}, result, duration_ms=int((time.time()-start)*1000))
    return result


def list_context() -> dict:
    """
    List all keys in the persistent context store with their last updated timestamps.

    Returns:
        dict with list of context keys and metadata.
    """
    start = time.time()
    keys = db.list_context_keys()
    result = {"context_keys": keys, "count": len(keys)}
    db.log_tool_call("list_context", {}, result, duration_ms=int((time.time()-start)*1000))
    return result
