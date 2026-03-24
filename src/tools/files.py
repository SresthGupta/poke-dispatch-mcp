"""
File system and git operation tools.

Provides directory listing, file reading/writing, content search,
and git integration.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from src import db
from src.config import MAX_FILE_READ_LINES, MAX_FILE_SIZE_MB


def list_files(path: str = ".", depth: int = 2) -> dict:
    """
    Recursively list files and directories up to a given depth.

    Args:
        path:  Root directory to list. Defaults to current directory.
        depth: Maximum directory depth to traverse. Defaults to 2.

    Returns:
        dict with tree structure and file count.
    """
    start = time.time()
    resolved = os.path.expanduser(path)
    if not os.path.exists(resolved):
        result = {"error": f"Path not found: {resolved}"}
        db.log_tool_call("list_files", {"path": path, "depth": depth}, result, success=False)
        return result

    entries = []

    def _walk(current: str, current_depth: int):
        if current_depth > depth:
            return
        try:
            items = sorted(os.listdir(current))
        except PermissionError:
            return
        for item in items:
            if item.startswith("."):
                continue
            full_path = os.path.join(current, item)
            rel_path = os.path.relpath(full_path, resolved)
            is_dir = os.path.isdir(full_path)
            entries.append({
                "path": rel_path,
                "type": "dir" if is_dir else "file",
                "depth": current_depth,
            })
            if is_dir:
                _walk(full_path, current_depth + 1)

    _walk(resolved, 0)
    result = {"root": resolved, "entries": entries, "count": len(entries)}
    db.log_tool_call("list_files", {"path": path, "depth": depth}, result, duration_ms=int((time.time()-start)*1000))
    return result


def read_file(path: str, lines: Optional[int] = None) -> dict:
    """
    Read a file's contents, optionally limiting to the first N lines.

    Args:
        path:  Absolute or relative path to the file.
        lines: Maximum number of lines to return. Reads all if not specified.

    Returns:
        dict with content, line count, and file size.
    """
    start = time.time()
    resolved = os.path.expanduser(path)
    if not os.path.isfile(resolved):
        result = {"error": f"File not found: {resolved}"}
        db.log_tool_call("read_file", {"path": path, "lines": lines}, result, success=False)
        return result

    size_mb = os.path.getsize(resolved) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        result = {"error": f"File too large ({size_mb:.1f} MB). Max is {MAX_FILE_SIZE_MB} MB."}
        db.log_tool_call("read_file", {"path": path, "lines": lines}, result, success=False)
        return result

    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        limit = lines or MAX_FILE_READ_LINES
        content = "".join(all_lines[:limit])
        result = {
            "path": resolved,
            "content": content,
            "total_lines": len(all_lines),
            "returned_lines": min(len(all_lines), limit),
            "truncated": len(all_lines) > limit,
        }
        db.log_tool_call("read_file", {"path": path, "lines": lines}, {"path": resolved, "lines_returned": result["returned_lines"]}, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("read_file", {"path": path, "lines": lines}, result, success=False)
        return result


def write_file(path: str, content: str) -> dict:
    """
    Create or overwrite a file with the given content.

    Creates parent directories automatically if they do not exist.

    Args:
        path:    Absolute or relative path for the new/updated file.
        content: Text content to write.

    Returns:
        dict with success status and bytes written.
    """
    start = time.time()
    resolved = os.path.expanduser(path)
    try:
        os.makedirs(os.path.dirname(resolved) or ".", exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
        result = {"success": True, "path": resolved, "bytes_written": len(content.encode("utf-8"))}
        db.log_tool_call("write_file", {"path": path}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("write_file", {"path": path}, result, success=False)
        return result


def search_files(path: str = ".", pattern: str = "*") -> dict:
    """
    Find files by name pattern within a directory tree.

    Args:
        path:    Root directory to search in.
        pattern: Glob pattern to match file names (e.g. '*.py', 'test_*').

    Returns:
        dict with list of matching file paths.
    """
    start = time.time()
    resolved = os.path.expanduser(path)
    if not os.path.isdir(resolved):
        result = {"error": f"Directory not found: {resolved}"}
        db.log_tool_call("search_files", {"path": path, "pattern": pattern}, result, success=False)
        return result

    matches = [str(p) for p in Path(resolved).rglob(pattern) if not any(part.startswith(".") for part in p.parts)]
    result = {"matches": matches, "count": len(matches), "pattern": pattern}
    db.log_tool_call("search_files", {"path": path, "pattern": pattern}, result, duration_ms=int((time.time()-start)*1000))
    return result


def search_code(path: str = ".", query: str = "") -> dict:
    """
    Search file contents for a text pattern using grep.

    Args:
        path:  Directory to search recursively.
        query: Search string or regex pattern.

    Returns:
        dict with matching lines grouped by file.
    """
    start = time.time()
    if not query:
        result = {"error": "Query string cannot be empty."}
        db.log_tool_call("search_code", {"path": path, "query": query}, result, success=False)
        return result

    resolved = os.path.expanduser(path)
    try:
        proc = subprocess.run(
            ["grep", "-rn", "--include=*.py", "--include=*.js", "--include=*.ts",
             "--include=*.go", "--include=*.java", "--include=*.rb", "--include=*.md",
             "-l", query, resolved],
            capture_output=True, text=True, timeout=30
        )
        files = [f for f in proc.stdout.strip().split("\n") if f]

        matches = {}
        for filepath in files[:20]:
            proc2 = subprocess.run(
                ["grep", "-n", query, filepath],
                capture_output=True, text=True, timeout=10
            )
            lines = [l for l in proc2.stdout.strip().split("\n") if l][:10]
            matches[filepath] = lines

        result = {"matches": matches, "files_found": len(files), "query": query}
        db.log_tool_call("search_code", {"path": path, "query": query}, {"files_found": len(files)}, duration_ms=int((time.time()-start)*1000))
        return result
    except subprocess.TimeoutExpired:
        result = {"error": "Search timed out."}
        db.log_tool_call("search_code", {"path": path, "query": query}, result, success=False)
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("search_code", {"path": path, "query": query}, result, success=False)
        return result


def git_status(repo: str = ".") -> dict:
    """
    Get the current git status of a repository.

    Args:
        repo: Path to the git repository. Defaults to current directory.

    Returns:
        dict with branch name, staged, unstaged, and untracked files.
    """
    start = time.time()
    resolved = os.path.expanduser(repo)
    try:
        def run_git(args):
            r = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=resolved, timeout=15)
            return r.stdout.strip()

        branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        status_out = run_git(["status", "--porcelain"])
        staged = [l[3:] for l in status_out.splitlines() if l[:2] in ("A ", "M ", "D ", "R ")]
        unstaged = [l[3:] for l in status_out.splitlines() if l[1:2] in ("M", "D") and l[0] == " "]
        untracked = [l[3:] for l in status_out.splitlines() if l[:2] == "??"]

        result = {
            "branch": branch,
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "clean": not bool(status_out),
        }
        db.log_tool_call("git_status", {"repo": repo}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("git_status", {"repo": repo}, result, success=False)
        return result


def git_log(repo: str = ".", n: int = 10) -> dict:
    """
    Get recent git commit history.

    Args:
        repo: Path to the git repository.
        n:    Number of recent commits to return.

    Returns:
        dict with list of commits including hash, author, date, and message.
    """
    start = time.time()
    resolved = os.path.expanduser(repo)
    try:
        proc = subprocess.run(
            ["git", "log", f"-{n}", "--pretty=format:%H|%an|%ad|%s", "--date=short"],
            capture_output=True, text=True, cwd=resolved, timeout=15
        )
        commits = []
        for line in proc.stdout.strip().splitlines():
            if "|" in line:
                parts = line.split("|", 3)
                commits.append({
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3] if len(parts) > 3 else "",
                })
        result = {"commits": commits, "count": len(commits)}
        db.log_tool_call("git_log", {"repo": repo, "n": n}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("git_log", {"repo": repo, "n": n}, result, success=False)
        return result
