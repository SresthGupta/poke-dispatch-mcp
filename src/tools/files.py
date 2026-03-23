import os
import fnmatch
import re
from pathlib import Path
from typing import Optional


def get_workspace_dir() -> Path:
    workspace = os.environ.get("WORKSPACE_DIR", "~/poke-workspace")
    return Path(workspace).expanduser().resolve()


def resolve_path(path: str) -> Path:
    """Resolve a path relative to the workspace directory."""
    workspace = get_workspace_dir()
    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)

    p = Path(path).expanduser()
    if p.is_absolute():
        resolved = p.resolve()
    else:
        resolved = (workspace / path).resolve()

    # Security: prevent path traversal outside workspace
    try:
        resolved.relative_to(workspace)
    except ValueError:
        raise ValueError(f"Path '{path}' is outside the workspace directory '{workspace}'")

    return resolved


def list_files(path: str = ".") -> str:
    """List directory contents."""
    try:
        target = resolve_path(path)
        if not target.exists():
            return f"Error: path '{path}' does not exist"
        if not target.is_dir():
            return f"Error: '{path}' is not a directory"

        entries = sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
        if not entries:
            return f"Directory '{path}' is empty"

        lines = [f"Contents of {target}:", ""]
        for entry in entries:
            if entry.is_dir():
                lines.append(f"  [DIR]  {entry.name}/")
            else:
                size = entry.stat().st_size
                size_str = _format_size(size)
                lines.append(f"  [FILE] {entry.name} ({size_str})")

        return "\n".join(lines)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error listing files: {e}"


def read_file(path: str) -> str:
    """Read file contents."""
    try:
        target = resolve_path(path)
        if not target.exists():
            return f"Error: file '{path}' does not exist"
        if not target.is_file():
            return f"Error: '{path}' is not a file"

        size = target.stat().st_size
        if size > 1_000_000:
            return f"Error: file is too large ({_format_size(size)}). Max size is 1 MB."

        content = target.read_text(encoding="utf-8", errors="replace")
        return content
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str) -> str:
    """Write content to a file, creating parent directories as needed."""
    try:
        target = resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"File written successfully: {target}"
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error writing file: {e}"


def search_files(path: str = ".", pattern: str = "*") -> str:
    """Search for files matching a glob pattern."""
    try:
        target = resolve_path(path)
        if not target.exists():
            return f"Error: path '{path}' does not exist"
        if not target.is_dir():
            return f"Error: '{path}' is not a directory"

        matches = []
        for root, dirs, files in os.walk(target):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for filename in files:
                if fnmatch.fnmatch(filename, pattern):
                    full_path = Path(root) / filename
                    try:
                        rel = full_path.relative_to(target)
                        matches.append(str(rel))
                    except ValueError:
                        matches.append(str(full_path))

        if not matches:
            return f"No files matching '{pattern}' found in '{path}'"

        matches.sort()
        lines = [f"Files matching '{pattern}' in '{path}':", ""]
        for m in matches[:200]:
            lines.append(f"  {m}")
        if len(matches) > 200:
            lines.append(f"  ... and {len(matches) - 200} more")
        return "\n".join(lines)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error searching files: {e}"


def search_content(path: str = ".", pattern: str = "") -> str:
    """Search for a regex pattern inside files."""
    if not pattern:
        return "Error: pattern cannot be empty"

    try:
        target = resolve_path(path)
        if not target.exists():
            return f"Error: path '{path}' does not exist"

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return f"Error: invalid regex pattern: {e}"

        results = []
        search_root = target if target.is_dir() else target.parent
        search_files_list = [target] if target.is_file() else []

        if target.is_dir():
            for root, dirs, files in os.walk(search_root):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                for filename in files:
                    if not filename.startswith("."):
                        search_files_list.append(Path(root) / filename)

        match_count = 0
        for filepath in search_files_list:
            if match_count >= 100:
                break
            try:
                text = filepath.read_text(encoding="utf-8", errors="replace")
                for lineno, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        try:
                            rel = filepath.relative_to(target if target.is_dir() else target.parent)
                        except ValueError:
                            rel = filepath
                        results.append(f"{rel}:{lineno}: {line.strip()}")
                        match_count += 1
                        if match_count >= 100:
                            break
            except Exception:
                continue

        if not results:
            return f"No matches for '{pattern}' in '{path}'"

        lines = [f"Matches for '{pattern}' in '{path}':", ""]
        lines.extend(results)
        if match_count >= 100:
            lines.append("... (truncated at 100 matches)")
        return "\n".join(lines)
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error searching content: {e}"


def _format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
