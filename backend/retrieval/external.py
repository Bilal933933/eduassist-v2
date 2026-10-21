"""بحث خارجي (ويكيبيديا) — المرحلة 4 (أداة مستقلة)."""

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger("eduassist.retrieval.external")

WIKIPEDIA_API = "https://{lang}.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY = "https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"

# Wikimedia ترفض العملاء بلا هوية واضحة (403).
WIKIPEDIA_HEADERS = {
    "User-Agent": (
        "EduAssist/0.1 (Arabic educational assistant; "
        "+https://github.com/Bilal933933/eduassist-v2)"
    )
}

# سقوف تحمي الموجّه من صفحات عامة ضخمة لا تخص الدرس.
MAX_WIKIPEDIA_PAGES = 6
MAX_EXTRACT_CHARS = 6000
MIN_EXTRACT_CHARS = 200


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
    async with httpx.AsyncClient(
        timeout=10.0, headers=WIKIPEDIA_HEADERS
    ) as client:
        for title in titles:
            summary = await _fetch_summary(client, title, lang)
            if summary:
                results.append(summary)

    return results


async def search_wikipedia_pages(
    query: str,
    lang: str = "ar",
    limit: int = MAX_WIKIPEDIA_PAGES,
    max_chars: int = MAX_EXTRACT_CHARS,
) -> list[dict[str, Any]]:
    """جلب النصوص الكاملة لصفحات ويكيبيديا ذات الصلة.

    ملف الدرس يحتاج تغطية كل المصادر، لا ملخصًا قصيرًا لكل صفحة، لذلك
    يجلب هذا المسار ``extracts`` كاملة مع الروابط، ويستبعد صفحات التوضيح
    والصفحات الفارغة، ويقطع النص عند سقف واضح.
    """
    if not query or not query.strip() or limit <= 0:
        return []

    titles = await _search_titles(query, lang, limit * 2)
    titles = list(dict.fromkeys(titles))[:limit]
    if not titles:
        return []

    async with httpx.AsyncClient(
        timeout=15.0, headers=WIKIPEDIA_HEADERS
    ) as client:
        # طلب كل صفحة منفردة: واجهة extracts قد تعيد نصًا فارغًا لأحد
        # العناوين عند طلب عدة صفحات في نداء واحد.
        pages = await asyncio.gather(
            *(
                _fetch_extract(client, title, lang, max_chars)
                for title in titles
            )
        )
    return [page for page in pages if page]


async def _fetch_extract(
    client: httpx.AsyncClient,
    title: str,
    lang: str,
    max_chars: int,
) -> dict[str, Any] | None:
    """جلب نص صفحة واحدة كاملًا مع استبعاد التوضيح والقصير."""
    url = WIKIPEDIA_API.format(lang=lang)
    params = {
        "action": "query",
        "prop": "extracts|info|pageprops",
        "explaintext": 1,
        "exsectionformat": "plain",
        "exlimit": 1,
        "inprop": "url",
        "ppprop": "disambiguation",
        "titles": title,
        "redirects": 1,
        "format": "json",
        "utf8": 1,
    }
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        pages = resp.json().get("query", {}).get("pages", {})
    except Exception as error:
        logger.warning("Wikipedia extract failed for %s: %s", title, error)
        return None

    for page in pages.values():
        if page.get("missing") is not None:
            continue
        if page.get("pageprops", {}).get("disambiguation") is not None:
            continue
        extract = str(page.get("extract") or "").strip()
        if len(extract) < MIN_EXTRACT_CHARS:
            continue
        return {
            "title": page.get("title", title),
            "url": page.get("fullurl", ""),
            "extract": extract[:max_chars],
            "truncated": len(extract) > max_chars,
            "source_type": "wikipedia",
        }
    return None


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
        async with httpx.AsyncClient(
            timeout=10.0, headers=WIKIPEDIA_HEADERS
        ) as client:
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
