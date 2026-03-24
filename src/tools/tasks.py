"""
Task planning and routing tools.

Uses the Anthropic API to intelligently break down tasks into subtasks,
route tasks to appropriate session types, and batch-start parallel sessions.
"""

import time
from typing import Optional

from src import db
from src.config import ANTHROPIC_API_KEY, DEFAULT_MODEL, SMART_MODEL
from src.tools.sessions import start_session


def plan_task(description: str, model: Optional[str] = None) -> dict:
    """
    Use the Anthropic API to break a high-level task into concrete subtasks.

    Each subtask includes a title, description, and recommended working directory.

    Args:
        description: High-level task description to plan.
        model:       Claude model to use. Defaults to the smart model.

    Returns:
        dict with the original task and a list of subtasks.
    """
    start = time.time()
    if not ANTHROPIC_API_KEY:
        result = {"error": "ANTHROPIC_API_KEY not set. Add it to your .env file."}
        db.log_tool_call("plan_task", {"description": description}, result, success=False)
        return result

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        chosen_model = model or SMART_MODEL

        prompt = f"""You are a software engineering assistant. Break the following task into 3-7 concrete subtasks that can each be executed by a separate Claude Code session.

Task: {description}

Respond in JSON only, no markdown fences. Format:
{{
  "task": "<original task>",
  "subtasks": [
    {{
      "title": "<short title>",
      "description": "<what Claude should do>",
      "cwd": "<suggested working directory or .>"
    }}
  ]
}}"""

        response = client.messages.create(
            model=chosen_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        text = response.content[0].text.strip()
        parsed = json.loads(text)
        result = parsed
        db.log_tool_call("plan_task", {"description": description, "model": chosen_model}, result, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("plan_task", {"description": description}, result, success=False)
        return result


def route_task(task: str, cwd: str = ".") -> dict:
    """
    Automatically determine the best session type for a task and start it.

    Uses keyword analysis to decide the appropriate Claude Code invocation
    and immediately starts the session.

    Args:
        task: Task description to route and start.
        cwd:  Working directory for the session.

    Returns:
        dict with session info and the routing decision.
    """
    start = time.time()
    task_lower = task.lower()

    # Simple keyword-based routing
    if any(kw in task_lower for kw in ["test", "pytest", "spec", "coverage"]):
        session_type = "testing"
    elif any(kw in task_lower for kw in ["deploy", "build", "docker", "ci", "pipeline"]):
        session_type = "devops"
    elif any(kw in task_lower for kw in ["refactor", "clean", "lint", "format"]):
        session_type = "refactoring"
    elif any(kw in task_lower for kw in ["review", "audit", "check", "analyze"]):
        session_type = "review"
    elif any(kw in task_lower for kw in ["debug", "fix", "bug", "error", "crash"]):
        session_type = "debugging"
    elif any(kw in task_lower for kw in ["write", "create", "implement", "add", "build"]):
        session_type = "development"
    else:
        session_type = "general"

    session_result = start_session(task, cwd)
    result = {**session_result, "route": session_type}
    db.log_tool_call("route_task", {"task": task, "cwd": cwd}, result, duration_ms=int((time.time()-start)*1000))
    return result


def batch_tasks(tasks: list[dict]) -> dict:
    """
    Start multiple Claude Code sessions in parallel for a list of tasks.

    Each task in the list should have 'task' and optionally 'cwd' keys.

    Args:
        tasks: List of task dicts, each with 'task' (str) and optional 'cwd' (str).

    Returns:
        dict with list of started sessions and any errors.
    """
    start = time.time()
    results = []
    errors = []

    for item in tasks:
        task_desc = item.get("task", "")
        cwd = item.get("cwd", ".")
        if not task_desc:
            errors.append({"error": "Empty task description", "item": item})
            continue
        session_result = start_session(task_desc, cwd)
        if "error" in session_result:
            errors.append({"error": session_result["error"], "task": task_desc})
        else:
            results.append(session_result)

    result = {
        "started": results,
        "failed": errors,
        "total_started": len(results),
        "total_failed": len(errors),
    }
    db.log_tool_call("batch_tasks", {"count": len(tasks)}, result, duration_ms=int((time.time()-start)*1000))
    return result
