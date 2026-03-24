"""
SQLite database layer for activity logging, session tracking, and context storage.

Tables:
  activity_log   - records every tool call with args, result, timestamp
  sessions       - tracks Claude Code subprocess sessions
  context_store  - persistent key/value memory
"""

import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Any, Optional

from src.config import DB_PATH


@contextmanager
def get_conn():
    """Context manager that yields a SQLite connection and commits on exit."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Create tables if they do not exist."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name   TEXT NOT NULL,
                args        TEXT,
                result      TEXT,
                success     INTEGER DEFAULT 1,
                duration_ms INTEGER,
                created_at  REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id  TEXT PRIMARY KEY,
                task        TEXT,
                cwd         TEXT,
                pid         INTEGER,
                status      TEXT DEFAULT 'running',
                started_at  REAL NOT NULL,
                ended_at    REAL,
                metadata    TEXT
            );

            CREATE TABLE IF NOT EXISTS context_store (
                key         TEXT PRIMARY KEY,
                value       TEXT,
                updated_at  REAL NOT NULL
            );
        """)


def log_tool_call(tool_name: str, args: dict, result: Any, success: bool = True, duration_ms: int = 0):
    """Log a tool call to activity_log."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO activity_log (tool_name, args, result, success, duration_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                tool_name,
                json.dumps(args, default=str),
                json.dumps(result, default=str)[:2000],
                1 if success else 0,
                duration_ms,
                time.time(),
            ),
        )


def get_activity_log(n: int = 50) -> list[dict]:
    """Return the most recent n activity log entries."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?", (n,)
        ).fetchall()
        return [dict(r) for r in rows]


# Session CRUD

def upsert_session(session_id: str, task: str, cwd: str, pid: int, status: str = "running", metadata: dict = None):
    """Insert or update a session record."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO sessions (session_id, task, cwd, pid, status, started_at, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                   pid=excluded.pid, status=excluded.status, metadata=excluded.metadata""",
            (
                session_id,
                task,
                cwd,
                pid,
                status,
                time.time(),
                json.dumps(metadata or {}),
            ),
        )


def update_session_status(session_id: str, status: str):
    """Update session status and optionally set ended_at."""
    with get_conn() as conn:
        if status in ("stopped", "completed", "error"):
            conn.execute(
                "UPDATE sessions SET status=?, ended_at=? WHERE session_id=?",
                (status, time.time(), session_id),
            )
        else:
            conn.execute(
                "UPDATE sessions SET status=? WHERE session_id=?",
                (status, session_id),
            )


def get_all_sessions() -> list[dict]:
    """Return all sessions ordered by start time descending."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_session(session_id: str) -> Optional[dict]:
    """Fetch a single session by ID."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_id=?", (session_id,)
        ).fetchone()
        return dict(row) if row else None


# Context store CRUD

def set_context(key: str, value: Any):
    """Persist a key/value pair."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO context_store (key, value, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
            (key, json.dumps(value, default=str), time.time()),
        )


def get_context(key: str) -> Optional[Any]:
    """Retrieve a stored context value by key."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM context_store WHERE key=?", (key,)
        ).fetchone()
        if row:
            return json.loads(row["value"])
        return None


def list_context_keys() -> list[dict]:
    """Return all context keys with last updated timestamp."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT key, updated_at FROM context_store ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


# Initialize on import
init_db()
