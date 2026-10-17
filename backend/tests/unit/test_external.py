"""اختبارات وحدة لـ search_wikipedia (mock للشبكة)."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from retrieval.external import search_wikipedia

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class _FakeClient:
    """عميل HTTP وهمي."""

    def __init__(self, responses):
        self._responses = responses
        self._idx = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def get(self, *a, **kw):
        resp = self._responses[self._idx]
        self._idx += 1
        return resp


def _make_resp(status=200, data=None, raise_err=None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = data or {}
    if raise_err:
        resp.raise_for_status = lambda: (_ for _ in ()).throw(raise_err)
    else:
        resp.raise_for_status = lambda: None
    return resp


def test_search_wikipedia_empty_query() -> None:
    """استعلام فارغ → قائمة فارغة."""
    result = asyncio.run(search_wikipedia(""))
    assert result == []
    result = asyncio.run(search_wikipedia("   "))
    assert result == []


def test_search_wikipedia_no_results() -> None:
    """لا توجد نتائج → قائمة فارغة."""
    search_resp = _make_resp(data={"query": {"search": []}})

    with patch("retrieval.external.httpx.AsyncClient", return_value=_FakeClient([search_resp])):
        result = asyncio.run(search_wikipedia("nonexistent_query_xyz"))
        assert result == []


def test_search_wikipedia_success() -> None:
    """بحث ناجح → نتائج مع title, snippet, url, source_type."""
    search_resp = _make_resp(data={"query": {"search": [{"title": "الفاعل"}, {"title": "النحو"}]}})
    summary_resp = _make_resp(data={
        "title": "الفاعل",
        "extract": "الفاعل هو من فعل الفعل...",
        "content_urls": {"desktop": {"page": "https://ar.wikipedia.org/wiki/الفاعل"}},
    })

    with patch("retrieval.external.httpx.AsyncClient", return_value=_FakeClient([search_resp, summary_resp, summary_resp])):
        result = asyncio.run(search_wikipedia("فاعل", top_k=2))
        assert len(result) >= 1
        assert result[0]["source_type"] == "wikipedia"
        assert "title" in result[0]
        assert "snippet" in result[0]
        assert "url" in result[0]


def test_search_wikipedia_network_error() -> None:
    """خطأ شبكة → قائمة فارغة (لا exception)."""

    class _ErrorClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, *a, **kw):
            raise Exception("Network error")

    with patch("retrieval.external.httpx.AsyncClient", return_value=_ErrorClient()):
        result = asyncio.run(search_wikipedia("test"))
        assert result == []

