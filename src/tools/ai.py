"""
AI utility tools powered by the Anthropic API.

Quick access to Claude for code generation, file analysis,
code review, and general Q&A.
"""

import time
from typing import Optional

from src import db
from src.config import ANTHROPIC_API_KEY, DEFAULT_MODEL, SMART_MODEL
from src.tools.files import read_file


def ask_claude(prompt: str, model: Optional[str] = None) -> dict:
    """
    Send a prompt to Claude and return the response.

    Uses the fast Haiku model by default for quick responses.
    Switch to a smarter model for complex tasks.

    Args:
        prompt: The question or instruction for Claude.
        model:  Claude model ID to use. Defaults to claude-haiku-4-5-20251001.

    Returns:
        dict with response text and token usage.
    """
    start = time.time()
    if not ANTHROPIC_API_KEY:
        result = {"error": "ANTHROPIC_API_KEY not set."}
        db.log_tool_call("ask_claude", {"prompt": prompt[:100]}, result, success=False)
        return result

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        chosen_model = model or DEFAULT_MODEL
        response = client.messages.create(
            model=chosen_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        result = {
            "response": text,
            "model": chosen_model,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        db.log_tool_call("ask_claude", {"model": chosen_model, "prompt_len": len(prompt)}, {"output_tokens": response.usage.output_tokens}, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("ask_claude", {"prompt": prompt[:100]}, result, success=False)
        return result


def analyze_file(path: str, question: str) -> dict:
    """
    Read a file and ask Claude a specific question about its contents.

    Args:
        path:     Path to the file to analyze.
        question: Specific question or instruction about the file.

    Returns:
        dict with Claude's analysis and the file path.
    """
    start = time.time()
    file_result = read_file(path)
    if "error" in file_result:
        db.log_tool_call("analyze_file", {"path": path, "question": question}, file_result, success=False)
        return file_result

    content = file_result.get("content", "")
    prompt = f"File: {path}\n\nContent:\n```\n{content[:6000]}\n```\n\nQuestion: {question}"
    claude_result = ask_claude(prompt, model=SMART_MODEL)
    result = {**claude_result, "file": path, "question": question}
    db.log_tool_call("analyze_file", {"path": path, "question": question}, {"model": claude_result.get("model")}, duration_ms=int((time.time()-start)*1000))
    return result


def generate_code(description: str, language: str = "python") -> dict:
    """
    Generate code based on a natural language description.

    Args:
        description: What the code should do.
        language:    Programming language to generate code in. Defaults to python.

    Returns:
        dict with generated code and explanation.
    """
    start = time.time()
    prompt = f"""Generate clean, well-commented {language} code for the following:

{description}

Provide only the code with brief inline comments. No markdown fences.
After the code, add a short one-paragraph explanation of how it works."""

    result = ask_claude(prompt, model=SMART_MODEL)
    if "response" in result:
        result["language"] = language
        result["description"] = description
    db.log_tool_call("generate_code", {"description": description[:100], "language": language}, {"model": result.get("model")}, duration_ms=int((time.time()-start)*1000))
    return result


def review_code(path: str) -> dict:
    """
    Perform a code review on a file, identifying bugs, issues, and improvements.

    Args:
        path: Path to the source file to review.

    Returns:
        dict with review findings organized by severity.
    """
    start = time.time()
    file_result = read_file(path)
    if "error" in file_result:
        db.log_tool_call("review_code", {"path": path}, file_result, success=False)
        return file_result

    content = file_result.get("content", "")
    prompt = f"""Review the following code in {path} for:
1. Bugs and logic errors
2. Security vulnerabilities
3. Performance issues
4. Code quality and readability
5. Missing error handling

Code:
```
{content[:6000]}
```

Respond in JSON with this structure:
{{
  "bugs": ["..."],
  "security": ["..."],
  "performance": ["..."],
  "quality": ["..."],
  "summary": "..."
}}"""

    try:
        import anthropic
        import json
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=SMART_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = {"raw_review": text}
        result = {**parsed, "file": path, "model": SMART_MODEL}
        db.log_tool_call("review_code", {"path": path}, {"file": path}, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("review_code", {"path": path}, result, success=False)
        return result
