"""
Configuration constants and paths for Poke Dispatch MCP server.
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
NOTES_DIR = DATA_DIR / "notes"
DB_PATH = DATA_DIR / "poke_dispatch.db"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
NOTES_DIR.mkdir(exist_ok=True)

# Server config
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
MCP_PATH = "/mcp"

# Anthropic API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
SMART_MODEL = "claude-sonnet-4-6"

# Session tracking
MAX_SESSIONS = 20
SESSION_TIMEOUT_SECONDS = 3600

# Blocked shell commands - dangerous operations that will be rejected
BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf ~",
    "rm -rf /*",
    "sudo rm",
    ":(){:|:&};:",
    "mkfs",
    "dd if=/dev/zero",
    "chmod -R 777 /",
    "chown -R",
    "> /dev/sda",
    "format c:",
    "shutdown",
    "reboot",
    "halt",
    "init 0",
    "init 6",
]

# Blocked command prefixes
BLOCKED_PREFIXES = [
    "sudo ",
    "su ",
]

# Timeout defaults
DEFAULT_COMMAND_TIMEOUT = 30
MAX_COMMAND_TIMEOUT = 300

# File read limits
MAX_FILE_READ_LINES = 1000
MAX_FILE_SIZE_MB = 10

# Render servers to monitor
RENDER_SERVERS = os.getenv("RENDER_SERVERS", "").split(",") if os.getenv("RENDER_SERVERS") else []

# Deploy mode: "render" disables tools that require local machine access.
# Set automatically via the RENDER environment variable on Render.com.
DEPLOY_MODE = "render" if os.getenv("RENDER") else "local"
