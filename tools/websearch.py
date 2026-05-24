"""General web search via SerpAPI (engine=google)."""

from __future__ import annotations

import os

import requests

_SERPAPI_BASE_URL = "https://serpapi.com/search"


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search the web via SerpAPI Google engine.

    Returns a list of dicts with keys: title, snippet, link.
    Raises ValueError if SERPAPI_API_KEY is not set.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError(
            "SERPAPI_API_KEY is not set — web search unavailable. "
            "Get a free key at https://serpapi.com"
        )

    params = {
        "engine": "google",
        "q": query,
        "api_key": api_key,
        "num": min(max_results, 10),
        "hl": "en",
        "gl": "us",
    }

    try:
        response = requests.get(_SERPAPI_BASE_URL, params=params, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Web search request failed: {exc}") from exc

    results = []
    for item in response.json().get("organic_results", [])[:max_results]:
        results.append({
            "title":   item.get("title", ""),
            "snippet": item.get("snippet", ""),
            "link":    item.get("link", ""),
        })
    return results
