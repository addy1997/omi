"""Web search and URL content extraction.

Uses DuckDuckGo (free, no API key) for search.
Uses Jina Reader (free, no API key) for URL content extraction.
"""
from __future__ import annotations

from typing import Annotated

import httpx
from langchain_core.tools import tool


@tool
def web_search(
    query: Annotated[str, "Search query"],
    max_results: Annotated[int, "Maximum number of results to return"] = 5,
) -> str:
    """Search the web using DuckDuckGo. No API key required."""
    try:
        from duckduckgo_search import DDGS  # type: ignore

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        lines = []
        for r in results:
            lines.append(f"**{r.get('title', '')}**\n{r.get('href', '')}\n{r.get('body', '')}")
        return "\n\n---\n\n".join(lines)
    except Exception as e:
        return f"Search error: {e}"


@tool
def fetch_url(
    url: Annotated[str, "URL to fetch and extract readable content from"],
) -> str:
    """Extract readable text from a URL using Jina Reader (r.jina.ai)."""
    try:
        jina_url = f"https://r.jina.ai/{url}"
        r = httpx.get(jina_url, timeout=20, follow_redirects=True,
                      headers={"Accept": "text/plain"})
        r.raise_for_status()
        text = r.text.strip()
        return text[:15_000] + "\n...(truncated)" if len(text) > 15_000 else text
    except Exception as e:
        return f"Failed to fetch {url}: {e}"


ALL_TOOLS = [web_search, fetch_url]
