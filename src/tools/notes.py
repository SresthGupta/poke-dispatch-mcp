import os
import re
from pathlib import Path
from datetime import datetime


def get_notes_dir() -> Path:
    notes_env = os.environ.get("NOTES_DIR", "")
    if notes_env:
        return Path(notes_env).expanduser().resolve()

    workspace_env = os.environ.get("WORKSPACE_DIR", "~/poke-workspace")
    workspace = Path(workspace_env).expanduser().resolve()
    return workspace / "notes"


def _safe_filename(title: str) -> str:
    """Convert a title to a safe filename."""
    safe = re.sub(r"[^\w\s-]", "", title)
    safe = re.sub(r"[\s_]+", "-", safe).strip("-")
    return safe.lower()[:100] or "untitled"


def create_note(title: str, content: str) -> str:
    """Save a markdown note to the notes directory."""
    if not title.strip():
        return "Error: title cannot be empty"

    try:
        notes_dir = get_notes_dir()
        notes_dir.mkdir(parents=True, exist_ok=True)

        filename = _safe_filename(title) + ".md"
        filepath = notes_dir / filename

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        note_content = f"# {title}\n\n_Created: {timestamp}_\n\n{content}\n"

        filepath.write_text(note_content, encoding="utf-8")
        return f"Note saved: {filepath}"
    except Exception as e:
        return f"Error creating note: {e}"


def list_notes() -> str:
    """List all saved notes."""
    try:
        notes_dir = get_notes_dir()
        if not notes_dir.exists():
            return "No notes directory found. Create a note first."

        notes = sorted(notes_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not notes:
            return "No notes found."

        lines = [f"Notes in {notes_dir}:", ""]
        for note in notes:
            mtime = datetime.fromtimestamp(note.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            # Try to read the first non-empty, non-header line as a preview
            preview = _get_preview(note)
            lines.append(f"  {note.stem}")
            lines.append(f"    Modified: {mtime}")
            if preview:
                lines.append(f"    Preview: {preview}")
            lines.append("")

        return "\n".join(lines).rstrip()
    except Exception as e:
        return f"Error listing notes: {e}"


def read_note(title: str) -> str:
    """Read a specific note by title."""
    if not title.strip():
        return "Error: title cannot be empty"

    try:
        notes_dir = get_notes_dir()
        filename = _safe_filename(title) + ".md"
        filepath = notes_dir / filename

        if not filepath.exists():
            # Try a case-insensitive search
            matches = list(notes_dir.glob("*.md")) if notes_dir.exists() else []
            for m in matches:
                if m.stem.lower() == _safe_filename(title).lower():
                    filepath = m
                    break
            else:
                available = [p.stem for p in matches] if matches else []
                if available:
                    return (
                        f"Note '{title}' not found. Available notes: "
                        + ", ".join(available[:10])
                    )
                return f"Note '{title}' not found. No notes exist yet."

        return filepath.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading note: {e}"


def _get_preview(path: Path) -> str:
    """Get a short preview of a note's content."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("_"):
                return stripped[:80] + ("..." if len(stripped) > 80 else "")
    except Exception:
        pass
    return ""
