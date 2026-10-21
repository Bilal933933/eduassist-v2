"""اختبارات جلب نصوص صفحات ويكيبيديا الكاملة."""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from retrieval.external import search_wikipedia_pages


class _FakeResponse:
    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeClient:
    def __init__(self, responses: list[_FakeResponse]) -> None:
        self._responses = responses
        self.requests: list[dict[str, Any]] = []

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def get(self, url: str, params: dict[str, Any] | None = None) -> _FakeResponse:
        self.requests.append({"url": url, "params": params or {}})
        return self._responses.pop(0)


def _search_payload(*titles: str) -> dict[str, Any]:
    return {"query": {"search": [{"title": title} for title in titles]}}


def _pages_payload(pages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "query": {
            "pages": {str(index): page for index, page in enumerate(pages)}
        }
    }


@pytest.mark.asyncio
async def test_returns_full_extracts_in_search_order() -> None:
    """يعيد النص الكامل والرابط لكل صفحة بترتيب البحث."""
    client = _FakeClient(
        [
            _FakeResponse(_search_payload("كان وأخواتها", "الأفعال الناسخة")),
            _FakeResponse(
                _pages_payload(
                    [
                        {
                            "title": "كان وأخواتها",
                            "fullurl": "https://ar.wikipedia.org/wiki/كان_وأخواتها",
                            "extract": "أ" * 300,
                        }
                    ]
                )
            ),
            _FakeResponse(
                _pages_payload(
                    [
                        {
                            "title": "الأفعال الناسخة",
                            "fullurl": "https://ar.wikipedia.org/wiki/الأفعال_الناسخة",
                            "extract": "ب" * 300,
                        }
                    ]
                )
            ),
        ]
    )

    with patch("retrieval.external.httpx.AsyncClient", return_value=client):
        results = await search_wikipedia_pages("كان وأخواتها", limit=2)

    assert [item["title"] for item in results] == ["كان وأخواتها", "الأفعال الناسخة"]
    assert results[0]["url"].endswith("كان_وأخواتها")
    assert results[0]["extract"] == "أ" * 300
    assert results[0]["source_type"] == "wikipedia"
    assert results[0]["truncated"] is False


@pytest.mark.asyncio
async def test_skips_missing_disambiguation_and_short_pages() -> None:
    """الصفحات الفارغة والتوضيحية والقصيرة لا تدخل ملف الدرس."""
    client = _FakeClient(
        [
            _FakeResponse(_search_payload("أ", "ب", "ج", "د")),
            _FakeResponse(
                _pages_payload([{"title": "أ", "missing": ""}])
            ),
            _FakeResponse(
                _pages_payload(
                    [
                        {
                            "title": "ب",
                            "pageprops": {"disambiguation": ""},
                            "extract": "ن" * 300,
                        }
                    ]
                )
            ),
            _FakeResponse(
                _pages_payload([{"title": "ج", "extract": "قصير"}])
            ),
            _FakeResponse(
                _pages_payload(
                    [
                        {
                            "title": "د",
                            "fullurl": "https://ar.wikipedia.org/wiki/د",
                            "extract": "د" * 300,
                        }
                    ]
                )
            ),
        ]
    )

    with patch("retrieval.external.httpx.AsyncClient", return_value=client):
        results = await search_wikipedia_pages("موضوع", limit=4)

    assert [item["title"] for item in results] == ["د"]


@pytest.mark.asyncio
async def test_truncates_long_extract_at_configured_limit() -> None:
    """النص الطويل يُقطع عند السقف ويُعلَّم أنه مقتطع."""
    client = _FakeClient(
        [
            _FakeResponse(_search_payload("درس")),
            _FakeResponse(
                _pages_payload(
                    [
                        {
                            "title": "درس",
                            "fullurl": "https://ar.wikipedia.org/wiki/درس",
                            "extract": "ن" * 500,
                        }
                    ]
                )
            ),
        ]
    )

    with patch("retrieval.external.httpx.AsyncClient", return_value=client):
        results = await search_wikipedia_pages("درس", limit=1, max_chars=250)

    assert len(results[0]["extract"]) == 250
    assert results[0]["truncated"] is True


@pytest.mark.asyncio
async def test_empty_query_does_not_call_network() -> None:
    """الاستعلام الفارغ يعيد قائمة فارغة بلا طلب شبكة."""
    with patch("retrieval.external.httpx.AsyncClient") as client:
        results = await search_wikipedia_pages("   ")

    assert results == []
    client.assert_not_called()
