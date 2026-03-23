import httpx
from bs4 import BeautifulSoup
from typing import Optional


def web_search(query: str, max_results: int = 8) -> str:
    """Search the web using DuckDuckGo and return results."""
    if not query.strip():
        return "Error: query cannot be empty"

    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No results found for: {query}"

        lines = [f"Web search results for: {query}", ""]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            href = r.get("href", "")
            body = r.get("body", "")
            lines.append(f"{i}. {title}")
            if href:
                lines.append(f"   URL: {href}")
            if body:
                snippet = body[:200] + ("..." if len(body) > 200 else "")
                lines.append(f"   {snippet}")
            lines.append("")

        return "\n".join(lines).rstrip()
    except ImportError:
        return "Error: duckduckgo-search package not installed. Run: pip install duckduckgo-search"
    except Exception as e:
        return f"Error performing web search: {e}"


def fetch_url(url: str) -> str:
    """Fetch a URL and extract readable text content."""
    if not url.strip():
        return "Error: URL cannot be empty"

    if not url.startswith(("http://", "https://")):
        return "Error: URL must start with http:// or https://"

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        with httpx.Client(timeout=15, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type or "application/xhtml" in content_type:
            return _parse_html(response.text, url)
        elif "text/" in content_type:
            return response.text[:10000]
        else:
            return f"Error: unsupported content type '{content_type}' for URL {url}"

    except httpx.TimeoutException:
        return f"Error: request timed out for {url}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP {e.response.status_code} for {url}"
    except Exception as e:
        return f"Error fetching URL: {e}"


def _parse_html(html: str, url: str) -> str:
    """Parse HTML and return cleaned text content."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove scripts, styles, nav, footer
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    # Try to get the main content
    title = soup.find("title")
    title_text = title.get_text(strip=True) if title else ""

    # Get text
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    # Remove very short lines that are likely nav remnants
    lines = [l for l in lines if len(l) > 10 or l.endswith(":")]
    content = "\n".join(lines)

    # Truncate if too long
    max_chars = 8000
    truncated = ""
    if len(content) > max_chars:
        content = content[:max_chars]
        truncated = f"\n\n[Content truncated at {max_chars} characters]"

    result_parts = []
    if title_text:
        result_parts.append(f"Title: {title_text}")
        result_parts.append(f"URL: {url}")
        result_parts.append("")
    result_parts.append(content)
    if truncated:
        result_parts.append(truncated)

    return "\n".join(result_parts)
