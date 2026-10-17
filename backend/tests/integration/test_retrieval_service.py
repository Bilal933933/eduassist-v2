"""اختبارات لـ RetrievalService (المرحلة 5)."""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from db.repositories.knowledge_repository import KnowledgeRepository
from db.session import open_session_factory
from retrieval.service import RetrievalService
from retrieval.tools import CurriculumRetrievalTools

_DIM = 768


def _vec(values: list[float]) -> list[float]:
    return values + [0.0] * (_DIM - len(values))


def _fake_embed(text: str) -> list[float]:
    return _vec([1.0, 0.0, 0.0])


asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _make_service(repo, tools) -> RetrievalService:
    return RetrievalService(repo, tools, _fake_embed, score_threshold=0.65)


def test_search_internal() -> None:
    """search_internal يعيد نتائج داخلية."""

    async def scenario() -> None:
        database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
        async with open_session_factory(database_url) as factory:
            async with factory() as session:
                from sqlalchemy import text

                await session.execute(text("DELETE FROM knowledge_chunks;"))
                await session.commit()
                repo = KnowledgeRepository(session)
                tools = CurriculumRetrievalTools(repo, _fake_embed)
                svc = _make_service(repo, tools)

                await repo.add_chunk(
                    content="نحو: الفاعل مرفوع",
                    embedding=_vec([1.0, 0.0, 0.0]),
                    subject="نحو",
                    grade="أول إعدادي",
                )
                await session.commit()

                results = await svc.search_internal(
                    query="test", subject="نحو", grade="أول إعدادي", top_k=5
                )
                assert len(results) >= 1
                assert results[0]["source_type"] == "curriculum"

    asyncio.run(scenario())


def test_search_external_mock() -> None:
    """search_external (mock) يعيد نتائج ويكيبيديا."""

    async def scenario() -> None:
        database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
        async with open_session_factory(database_url) as factory:
            async with factory() as session:
                repo = KnowledgeRepository(session)
                tools = CurriculumRetrievalTools(repo, _fake_embed)
                svc = _make_service(repo, tools)

                search_resp = MagicMock()
                search_resp.status_code = 200
                search_resp.json.return_value = {"query": {"search": [{"title": "الفاعل"}]}}
                search_resp.raise_for_status = lambda: None

                summary_resp = MagicMock()
                summary_resp.status_code = 200
                summary_resp.json.return_value = {
                    "title": "الفاعل",
                    "extract": "الفاعل هو من فعل الفعل...",
                    "content_urls": {"desktop": {"page": "https://ar.wikipedia.org/wiki/الفاعل"}},
                }

                class _FakeClient:
                    def __init__(self):
                        self._idx = 0
                        self._resps = [search_resp, summary_resp]

                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, *a):
                        pass

                    async def get(self, *a, **kw):
                        r = self._resps[self._idx]
                        self._idx += 1
                        return r

                with patch("retrieval.external.httpx.AsyncClient", return_value=_FakeClient()):
                    results = await svc.search_external(query="فاعل", top_k=2)
                    assert len(results) >= 1
                    assert results[0]["source_type"] == "wikipedia"

    asyncio.run(scenario())


def test_search_hybrid_no_external_when_good() -> None:
    """hybrid: نتائج داخلية جيدة → لا استدعاء خارجي."""

    async def scenario() -> None:
        database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
        async with open_session_factory(database_url) as factory:
            async with factory() as session:
                from sqlalchemy import text
                await session.execute(text("DELETE FROM knowledge_chunks;"))
                await session.commit()
                repo = KnowledgeRepository(session)
                tools = CurriculumRetrievalTools(repo, _fake_embed)
                svc = _make_service(repo, tools)

                await repo.add_chunk(
                    content="نحو: الفاعل مرفوع",
                    embedding=_vec([1.0, 0.0, 0.0]),
                    subject="نحو",
                    grade="أول إعدادي",
                )
                await session.commit()

                results = await svc.search_hybrid(
                    query="test", subject="نحو", grade="أول إعدادي", top_k=5
                )
                assert len(results) == 1
                assert results[0]["source_type"] == "curriculum"

    asyncio.run(scenario())


def test_search_hybrid_triggers_external_on_empty() -> None:
    """hybrid: لا نتائج داخلية → استدعاء خارجي."""

    async def scenario() -> None:
        database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
        async with open_session_factory(database_url) as factory:
            async with factory() as session:
                repo = KnowledgeRepository(session)
                tools = CurriculumRetrievalTools(repo, _fake_embed)
                svc = _make_service(repo, tools)

                search_resp = _make_search_resp([{"title": "الفاعل"}])
                summary_resp = _make_summary_resp()

                class _FakeClient:
                    def __init__(self):
                        self._idx = 0
                        self._resps = [search_resp, summary_resp]

                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, *a):
                        pass

                    async def get(self, *a, **kw):
                        r = self._resps[self._idx]
                        self._idx += 1
                        return r

                with patch("retrieval.external.httpx.AsyncClient", return_value=_FakeClient()):
                    results = await svc.search_hybrid(
                        query="فاعل", subject="نحو", grade="أول إعدادي", top_k=5
                    )
                    # Should have external result
                    assert any(r.get("source_type") == "wikipedia" for r in results)

    asyncio.run(scenario())


def _make_search_resp(items):
    from unittest.mock import MagicMock

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"query": {"search": items}}
    resp.raise_for_status = lambda: None
    return resp


def _make_summary_resp():
    from unittest.mock import MagicMock

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "title": "الفاعل",
        "extract": "الفاعل هو من فعل الفعل...",
        "content_urls": {"desktop": {"page": "https://ar.wikipedia.org/wiki/الفاعل"}},
    }
    return resp
