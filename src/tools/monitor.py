"""
Health monitoring and dashboard tools.

Check the status of Render servers, Claude Code sessions,
and display a consolidated system dashboard.
"""

import time
from typing import Optional

import httpx

from src import db
from src.config import RENDER_SERVERS


def check_health() -> dict:
    """
    Ping configured Render servers and check active session health.

    Render server URLs are read from the RENDER_SERVERS environment variable
    (comma-separated list of URLs).

    Returns:
        dict with server statuses and session summary.
    """
    start = time.time()
    server_results = []
    for url in RENDER_SERVERS:
        url = url.strip()
        if not url:
            continue
        t0 = time.time()
        try:
            resp = httpx.get(url, timeout=10, follow_redirects=True)
            server_results.append({
                "url": url,
                "status": resp.status_code,
                "healthy": resp.status_code < 400,
                "latency_ms": int((time.time() - t0) * 1000),
            })
        except Exception as e:
            server_results.append({
                "url": url,
                "status": None,
                "healthy": False,
                "error": str(e),
                "latency_ms": int((time.time() - t0) * 1000),
            })

    sessions = db.get_all_sessions()
    running = [s for s in sessions if s["status"] == "running"]

    result = {
        "servers": server_results,
        "servers_healthy": sum(1 for s in server_results if s.get("healthy")),
        "servers_total": len(server_results),
        "sessions_running": len(running),
        "sessions_total": len(sessions),
        "checked_at": time.time(),
    }
    db.log_tool_call("check_health", {}, result, duration_ms=int((time.time()-start)*1000))
    return result


def get_dashboard() -> dict:
    """
    Return a formatted text summary of the entire Poke Dispatch system.

    Includes session counts, recent activity, server health, and system resources.

    Returns:
        dict with formatted dashboard text and raw data.
    """
    start = time.time()
    import psutil

    sessions = db.get_all_sessions()
    running = [s for s in sessions if s["status"] == "running"]
    recent_activity = db.get_activity_log(10)
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.2)

    lines = [
        "=== POKE DISPATCH DASHBOARD ===",
        "",
        f"Sessions: {len(running)} running / {len(sessions)} total",
    ]
    for s in running[:5]:
        lines.append(f"  [{s['session_id']}] {s['task'][:60]} (PID {s['pid']})")

    lines += [
        "",
        f"System: CPU {cpu:.1f}%  RAM {mem.percent:.1f}%",
        "",
        "Recent Activity (last 10 calls):",
    ]
    for entry in recent_activity:
        status = "OK" if entry.get("success") else "ERR"
        ts = time.strftime("%H:%M:%S", time.localtime(entry.get("created_at", 0)))
        lines.append(f"  [{ts}] {status} {entry['tool_name']} ({entry.get('duration_ms', 0)}ms)")

    if RENDER_SERVERS:
        lines += ["", "Render Servers:"]
        for url in RENDER_SERVERS:
            url = url.strip()
            if url:
                lines.append(f"  {url}")

    dashboard_text = "\n".join(lines)
    result = {
        "dashboard": dashboard_text,
        "sessions_running": len(running),
        "sessions_total": len(sessions),
        "cpu_percent": cpu,
        "ram_percent": mem.percent,
    }
    db.log_tool_call("get_dashboard", {}, {"sessions_running": len(running)}, duration_ms=int((time.time()-start)*1000))
    return result


def get_activity_log(n: int = 50) -> dict:
    """
    Return the most recent tool call activity log entries.

    Args:
        n: Number of recent log entries to return. Defaults to 50.

    Returns:
        dict with list of activity log entries.
    """
    start = time.time()
    entries = db.get_activity_log(n)
    result = {"entries": entries, "count": len(entries)}
    db.log_tool_call("get_activity_log", {"n": n}, {"count": len(entries)}, duration_ms=int((time.time()-start)*1000))
    return result
