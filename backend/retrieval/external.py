"""بحث خارجي (ويكيبيديا) — المرحلة 4 (أداة مستقلة)."""

import logging
from typing import Any

import httpx

logger = logging.getLogger("eduassist.retrieval.external")

WIKIPEDIA_API = "https://{lang}.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"


async def search_wikipedia(
    query: str,
    lang: str = "ar",
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """بحث في ويكيبيديا وإرجاع ملخصات.

    Args:
        query: استعلام البحث.
        lang: رمز اللغة (ar, en, ...).
        top_k: عدد النتائج.

    Returns:
        list of {title, snippet, url, source_type: "wikipedia"}.
    """
    if not query or not query.strip():
        return []

    titles = await _search_titles(query, lang, top_k)
    if not titles:
        return []

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for title in titles:
            summary = await _fetch_summary(client, title, lang)
            if summary:
                results.append(summary)

    return results


async def _search_titles(query: str, lang: str, top_k: int) -> list[str]:
    """بحث ويكيبيديا → قائمة عناوين."""
    url = WIKIPEDIA_API.format(lang=lang)
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": top_k,
        "format": "json",
        "utf8": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return [item["title"] for item in data.get("query", {}).get("search", [])]
    except Exception as e:
        logger.warning("Wikipedia search failed: %s", e)
        return []


async def _fetch_summary(
    client: httpx.AsyncClient, title: str, lang: str
) -> dict[str, Any] | None:
    """جلب ملخص صفحة ويكيبيديا."""
    url = WIKIPEDIA_SUMMARY.format(lang=lang, title=title.replace(" ", "_"))
    try:
        resp = await client.get(url)
        if resp.status_code != 200:
            return None
        data = resp.json()
        extract = data.get("extract", "")
        if not extract:
            return None
        return {
            "title": data.get("title", title),
            "snippet": extract[:500],
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            "source_type": "wikipedia",
        }
    except Exception as e:
        logger.warning("Wikipedia summary failed for %s: %s", title, e)
        return None
