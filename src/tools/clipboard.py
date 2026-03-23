def get_clipboard() -> str:
    """Read the current clipboard contents."""
    try:
        import pyperclip
        content = pyperclip.paste()
        if content is None:
            return "Clipboard is empty"
        if not content:
            return "Clipboard is empty"
        if len(content) > 10000:
            return content[:10000] + f"\n\n[Clipboard content truncated at 10000 characters, full length: {len(content)}]"
        return content
    except ImportError:
        return "Error: pyperclip not installed. Run: pip install pyperclip"
    except Exception as e:
        return f"Error reading clipboard: {e}"


def set_clipboard(text: str) -> str:
    """Write text to the clipboard."""
    if text is None:
        return "Error: text cannot be None"
    try:
        import pyperclip
        pyperclip.copy(text)
        preview = text[:100] + ("..." if len(text) > 100 else "")
        return f"Clipboard updated ({len(text)} characters). Preview: {preview}"
    except ImportError:
        return "Error: pyperclip not installed. Run: pip install pyperclip"
    except Exception as e:
        return f"Error writing to clipboard: {e}"
