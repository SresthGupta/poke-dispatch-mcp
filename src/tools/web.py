"""
Web tools for searching and fetching content from the internet.

Provides DuckDuckGo search, URL fetching with text extraction,
and Claude-powered URL summarization.
"""

import time
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from src import db
from src.config import ANTHROPIC_API_KEY, DEFAULT_MODEL


def web_search(query: str, max_results: int = 8) -> dict:
    """
    Search the web using DuckDuckGo and return top results.

    Args:
        query:       Search query string.
        max_results: Maximum number of results to return. Defaults to 8.

    Returns:
        dict with list of results containing title, url, and snippet.
    """
    start = time.time()
    if not query.strip():
        result = {"error": "Search query cannot be empty."}
        db.log_tool_call("web_search", {"query": query}, result, success=False)
        return result

    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        result = {"results": results, "count": len(results), "query": query}
        db.log_tool_call("web_search", {"query": query, "max_results": max_results}, {"count": len(results)}, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("web_search", {"query": query}, result, success=False)
        return result


def fetch_url(url: str, timeout: int = 15) -> dict:
    """
    Fetch a URL and extract readable text content.

    Strips HTML tags and returns clean text suitable for further processing.

    Args:
        url:     Full URL to fetch (must start with http:// or https://).
        timeout: Request timeout in seconds. Defaults to 15.

    Returns:
        dict with text content, title, and word count.
    """
    start = time.time()
    if not url.startswith(("http://", "https://")):
        result = {"error": "URL must start with http:// or https://"}
        db.log_tool_call("fetch_url", {"url": url}, result, success=False)
        return result

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; PokeDispatch/1.0)"}
        resp = httpx.get(url, timeout=timeout, headers=headers, follow_redirects=True)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove scripts and styles
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title else ""
        text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        import re
        text = re.sub(r"\s+", " ", text).strip()[:8000]

        result = {
            "url": url,
            "title": title,
            "content": text,
            "word_count": len(text.split()),
            "status_code": resp.status_code,
        }
        db.log_tool_call("fetch_url", {"url": url}, {"title": title, "words": len(text.split())}, duration_ms=int((time.time()-start)*1000))
        return result
    except httpx.HTTPStatusError as e:
        result = {"error": f"HTTP {e.response.status_code}: {url}"}
        db.log_tool_call("fetch_url", {"url": url}, result, success=False)
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("fetch_url", {"url": url}, result, success=False)
        return result


def summarize_url(url: str, question: Optional[str] = None) -> dict:
    """
    Fetch a URL and ask Claude to summarize or answer a question about it.

    Args:
        url:      Full URL to fetch and analyze.
        question: Optional specific question to answer about the content.
                  If not provided, generates a general summary.

    Returns:
        dict with summary text and source URL.
    """
    start = time.time()
    if not ANTHROPIC_API_KEY:
        result = {"error": "ANTHROPIC_API_KEY not set. Cannot summarize without API access."}
        db.log_tool_call("summarize_url", {"url": url, "question": question}, result, success=False)
        return result

    fetch_result = fetch_url(url)
    if "error" in fetch_result:
        db.log_tool_call("summarize_url", {"url": url}, fetch_result, success=False)
        return fetch_result

    content = fetch_result.get("content", "")
    title = fetch_result.get("title", url)

    prompt = question or "Please provide a concise summary of this content."
    full_prompt = f"URL: {url}\nTitle: {title}\n\nContent:\n{content[:4000]}\n\nTask: {prompt}"

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": full_prompt}],
        )
        summary = response.content[0].text.strip()
        result = {"url": url, "title": title, "summary": summary, "question": question}
        db.log_tool_call("summarize_url", {"url": url, "question": question}, {"words": len(summary.split())}, duration_ms=int((time.time()-start)*1000))
        return result
    except Exception as e:
        result = {"error": str(e)}
        db.log_tool_call("summarize_url", {"url": url, "question": question}, result, success=False)
        return result
