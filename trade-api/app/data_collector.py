"""
Data collector – fetches recent news & market data for a sector
using DuckDuckGo's HTML search (no API key required).
"""

import asyncio
import logging
import re
import urllib.parse
from typing import List, Dict, Any

import httpx

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
_TIMEOUT = 10  # seconds per request


async def _ddg_search(query: str, max_results: int = 8) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo (HTML endpoint) and return a list of
    {title, url, snippet} dicts.
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"

    try:
        async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True, timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:
        logger.warning("DuckDuckGo search failed for '%s': %s", query, exc)
        return []

    # ── Very lightweight HTML parsing (no BeautifulSoup dependency) ──────────
    results: List[Dict[str, str]] = []

    # Each result block looks like:
    #   <a class="result__a" href="...">Title</a>
    #   <a class="result__snippet">Snippet</a>
    title_pattern = re.compile(
        r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', re.DOTALL
    )
    snippet_pattern = re.compile(
        r'class="result__snippet"[^>]*>(.*?)</a>', re.DOTALL
    )

    titles = title_pattern.findall(html)
    snippets = [m.group(1) for m in snippet_pattern.finditer(html)]

    for i, (href, title) in enumerate(titles[:max_results]):
        snippet = snippets[i] if i < len(snippets) else ""
        results.append({
            "title": _strip_tags(title).strip(),
            "url": href,
            "snippet": _strip_tags(snippet).strip(),
        })

    logger.debug("DDG search '%s' → %d results", query, len(results))
    return results


def _strip_tags(text: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", text)


# ── Public interface ──────────────────────────────────────────────────────────

async def collect_sector_data(sector: str) -> Dict[str, Any]:
    """
    Run several parallel searches to gather broad context about the sector.

    Returns a dict with keys:
        - queries: list of queries run
        - results: list of {title, url, snippet} dicts (deduplicated)
        - summary_text: plain-text block suitable for prompting an LLM
    """
    queries = [
        f"India {sector} sector trade opportunities 2024 2025",
        f"India {sector} exports imports market trends",
        f"India {sector} industry growth challenges policy",
        f"India {sector} sector key companies market size",
    ]

    tasks = [_ddg_search(q, max_results=5) for q in queries]
    all_results_nested = await asyncio.gather(*tasks, return_exceptions=True)

    seen_urls: set = set()
    merged: List[Dict[str, str]] = []
    for batch in all_results_nested:
        if isinstance(batch, Exception):
            continue
        for item in batch:
            if item["url"] not in seen_urls and item["title"]:
                seen_urls.add(item["url"])
                merged.append(item)

    # Build a text block for the LLM
    lines: List[str] = []
    for r in merged:
        lines.append(f"### {r['title']}")
        if r["snippet"]:
            lines.append(r["snippet"])
        lines.append(f"Source: {r['url']}")
        lines.append("")

    summary_text = "\n".join(lines) if lines else "No web results retrieved."
    logger.info("Collected %d web snippets for sector '%s'", len(merged), sector)

    return {
        "queries": queries,
        "results": merged,
        "summary_text": summary_text,
    }
