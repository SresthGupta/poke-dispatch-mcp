import os
from dotenv import load_dotenv
from fastmcp import FastMCP

from tools.files import list_files, read_file, write_file, search_files, search_content
from tools.web import web_search, fetch_url
from tools.system import run_command, get_system_info
from tools.notes import create_note, list_notes, read_note
from tools.clipboard import get_clipboard, set_clipboard

load_dotenv()

mcp = FastMCP("Poke Dispatch MCP")

# ---------------------------------------------------------------------------
# File Management Tools
# ---------------------------------------------------------------------------


@mcp.tool(description="List the contents of a directory. Defaults to the workspace root.")
def tool_list_files(path: str = ".") -> str:
    return list_files(path)


@mcp.tool(description="Read the contents of a file within the workspace.")
def tool_read_file(path: str) -> str:
    return read_file(path)


@mcp.tool(description="Write content to a file within the workspace, creating it if it does not exist.")
def tool_write_file(path: str, content: str) -> str:
    return write_file(path, content)


@mcp.tool(description="Search for files by name pattern (supports glob wildcards like *.txt) within a directory.")
def tool_search_files(path: str = ".", pattern: str = "*") -> str:
    return search_files(path, pattern)


@mcp.tool(description="Search for a regex pattern inside file contents (like grep). Returns matching lines with filenames and line numbers.")
def tool_search_content(path: str = ".", pattern: str = "") -> str:
    return search_content(path, pattern)


# ---------------------------------------------------------------------------
# Web Tools
# ---------------------------------------------------------------------------


@mcp.tool(description="Search the web using DuckDuckGo and return titles, URLs, and snippets.")
def tool_web_search(query: str, max_results: int = 8) -> str:
    return web_search(query, max_results)


@mcp.tool(description="Fetch a URL and extract readable text content from the page.")
def tool_fetch_url(url: str) -> str:
    return fetch_url(url)


# ---------------------------------------------------------------------------
# System Tools
# ---------------------------------------------------------------------------


@mcp.tool(description="Execute a shell command. Dangerous commands (rm -rf /, sudo, shutdown, etc.) are blocked.")
def tool_run_command(command: str, timeout: int = 30) -> str:
    return run_command(command, timeout)


@mcp.tool(description="Get system information including OS, CPU, memory, and disk usage.")
def tool_get_system_info() -> str:
    return get_system_info()


# ---------------------------------------------------------------------------
# Note Tools
# ---------------------------------------------------------------------------


@mcp.tool(description="Save a markdown note with a title and content to the notes directory.")
def tool_create_note(title: str, content: str) -> str:
    return create_note(title, content)


@mcp.tool(description="List all saved notes with modification times and previews.")
def tool_list_notes() -> str:
    return list_notes()


@mcp.tool(description="Read a specific note by its title.")
def tool_read_note(title: str) -> str:
    return read_note(title)


# ---------------------------------------------------------------------------
# Clipboard Tools
# ---------------------------------------------------------------------------


@mcp.tool(description="Read the current contents of the system clipboard.")
def tool_get_clipboard() -> str:
    return get_clipboard()


@mcp.tool(description="Write text to the system clipboard.")
def tool_set_clipboard(text: str) -> str:
    return set_clipboard(text)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Poke Dispatch MCP server on port {port}")
    print(f"Workspace: {os.environ.get('WORKSPACE_DIR', '~/poke-workspace')}")
    print(f"MCP endpoint: http://localhost:{port}/mcp")
    mcp.run(transport="http", host="0.0.0.0", port=port, stateless_http=True)
