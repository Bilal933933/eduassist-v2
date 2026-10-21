"""اختبارات لـ RetrievalService (المرحلة 5)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from db.repositories.knowledge_repository import KnowledgeRepository
from db.session import open_session_factory
from retrieval.service import RetrievalService, _filter_topic_pages

_DIM = 768


def _vec(values: list[float]) -> list[float]:
    return values + [0.0] * (_DIM - len(values))


async def _fake_embed(text: str) -> list[float]:
    _ = text
    return _vec([1.0, 0.0, 0.0])


asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def _make_service(factory) -> RetrievalService:
    return RetrievalService(factory, _fake_embed, score_threshold=0.65)


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
                svc = _make_service(factory)

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
                svc = _make_service(factory)

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
                svc = _make_service(factory)

                for index in range(5):
                    await repo.add_chunk(
                        content=f"نحو: الفاعل مرفوع {index}",
                        embedding=_vec([1.0, 0.0, 0.0]),
                        subject="نحو",
                        grade="أول إعدادي",
                    )
                await session.commit()

                with patch(
                    "retrieval.service.search_wikipedia", new=AsyncMock()
                ) as external:
                    results = await svc.search_hybrid(
                        query="test", subject="نحو", grade="أول إعدادي", top_k=5
                    )

                external.assert_not_awaited()
                assert len(results) == 5
                assert all(
                    result["source_type"] == "curriculum" for result in results
                )

    asyncio.run(scenario())


def test_search_hybrid_triggers_external_on_empty() -> None:
    """hybrid: لا نتائج داخلية → استدعاء خارجي."""

    async def scenario() -> None:
        database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
        async with open_session_factory(database_url) as factory:
            async with factory() as session:
                from sqlalchemy import text

                await session.execute(text("DELETE FROM knowledge_chunks;"))
                await session.commit()
                svc = _make_service(factory)

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

def test_search_lesson_sources_collects_all_grades_and_scopes() -> None:
    """ملف الدرس يجمع كل الصفوف ويوسّع كل نطاق لكل مقاطعه."""

    async def scenario() -> None:
        database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
        async with open_session_factory(database_url) as factory:
            async with factory() as session:
                from sqlalchemy import text

                await session.execute(text("DELETE FROM knowledge_chunks;"))
                await session.commit()
                repo = KnowledgeRepository(session)
                svc = _make_service(factory)

                for index in range(12):
                    await repo.add_chunk(
                        content=f"مقطع غير مرتبط {index}",
                        embedding=_vec([0.99, 0.01, 0.0]),
                        subject="نحو",
                        grade="ثالث إعدادي",
                        chapter="درس آخر",
                        source="آخر.md",
                    )
                await repo.add_chunk(
                    content="تعريف كان وأخواتها",
                    embedding=_vec([1.0, 0.0, 0.0]),
                    subject="نحو",
                    grade="أول إعدادي",
                    chapter="كان وأخواتها",
                    source="نحو.md",
                )
                await repo.add_chunk(
                    content="مقطع بعيد في الدرس نفسه",
                    embedding=_vec([0.0, 1.0, 0.0]),
                    subject="نحو",
                    grade="أول إعدادي",
                    chapter="كان وأخواتها",
                    source="نحو.md",
                )
                await repo.add_chunk(
                    content="شرح كان وأخواتها للصف الثاني",
                    embedding=_vec([1.0, 0.0, 0.0]),
                    subject="نحو",
                    grade="ثاني إعدادي",
                    chapter="كان وأخواتها",
                    source="نحو-٢.md",
                )
                await repo.add_chunk(
                    content="درس آخر في المصدر نفسه",
                    embedding=_vec([1.0, 0.0, 0.0]),
                    subject="نحو",
                    grade="أول إعدادي",
                    chapter="درس آخر",
                    source="نحو.md",
                )
                await session.commit()

                with patch(
                    "retrieval.service.search_wikipedia_pages",
                    new=AsyncMock(return_value=[]),
                ):
                    sources = await svc.search_lesson_sources(
                        "كان وأخواتها", subject="نحو"
                    )

                target_sources = [
                    source
                    for source in sources
                    if source["title"] == "كان وأخواتها"
                ]
                assert len(target_sources) == 2
                assert all(
                    source["title"] == "كان وأخواتها" for source in sources
                )
                grades = {grade for source in target_sources for grade in source["grades"]}
                assert grades == {"أول إعدادي", "ثاني إعدادي"}
                assert any(
                    "مقطع بعيد في الدرس نفسه" in source["text"]
                    for source in target_sources
                )
                assert all(
                    "درس آخر في المصدر نفسه" not in source["text"]
                    for source in target_sources
                )

    asyncio.run(scenario())


def test_search_lesson_sources_falls_back_to_wikipedia() -> None:
    """بلا منهج مفهرس يعود ملف الدرس بصفحات ويكيبيديا."""

    async def scenario() -> None:
        database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
        async with open_session_factory(database_url) as factory:
            async with factory() as session:
                from sqlalchemy import text

                await session.execute(text("DELETE FROM knowledge_chunks;"))
                await session.commit()
                svc = _make_service(factory)
                page = {
                    "title": "كان وأخواتها",
                    "url": "https://ar.wikipedia.org/wiki/كان_وأخواتها",
                    "extract": "ن" * 300,
                    "truncated": False,
                }

                with patch(
                    "retrieval.service.search_wikipedia_pages",
                    new=AsyncMock(return_value=[page]),
                ) as wikipedia:
                    sources = await svc.search_lesson_sources(
                        "كان وأخواتها", subject="نحو"
                    )

                assert len(sources) == 1
                assert sources[0]["kind"] == "wikipedia"
                assert sources[0]["grades"] == []
                wikipedia.assert_awaited_once()
                assert (
                    wikipedia.await_args.kwargs["query"]
                    == "كان وأخواتها في نحو"
                )

    asyncio.run(scenario())


def test_filter_topic_pages_keeps_only_lesson_titles() -> None:
    pages = [
        {"title": "الخبر (السعودية)"},
        {"title": "خبر (نحو)"},
        {"title": "إن وأخواتها"},
    ]

    filtered = _filter_topic_pages(pages, "الخبر", "النحو")

    assert [page["title"] for page in filtered] == ["خبر (نحو)"]
