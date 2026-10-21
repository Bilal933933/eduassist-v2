"""اختبارات عقدة ملف الدرس المعرفي."""

import asyncio
from typing import Any

from orchestration.nodes.teacher.lesson_info import (
    _clean_topic,
    create_lesson_info_node,
)
from prompts.tasks.lesson_info import (
    LESSON_INFO_COMPOSE_TASK,
    LESSON_INFO_EXTRACT_TASK,
)


def _source(
    title: str = "كان وأخواتها",
    grade: str = "أول إعدادي",
    text: str = "كان وأخواتها أفعال ناسخة ترفع الاسم وتنصب الخبر.",
    *,
    kind: str = "curriculum",
    url: str = "",
) -> dict[str, Any]:
    return {
        "kind": kind,
        "title": title,
        "text": text,
        "url": url,
        "grades": [grade] if grade else [],
        "chapter": title,
        "source": "نحو.md",
        "truncated": False,
    }


class FakeRetrieval:
    def __init__(self, sources: list[dict[str, Any]]) -> None:
        self.sources = sources
        self.calls: list[tuple[str, str | None]] = []

    async def search_lesson_sources(
        self, query: str, subject: str | None = None
    ) -> list[dict[str, Any]]:
        self.calls.append((query, subject))
        return self.sources


class FakeModel:
    def __init__(
        self,
        response: str = "## كان وأخواتها\n[1] تعريف.\n[2] تفصيل.",
        error=None,
    ):
        self.response = response
        self.error = error
        self.calls: list[tuple[str, str, float]] = []

    async def __call__(
        self, task: str, system_prompt: str, temperature: float
    ) -> str:
        self.calls.append((task, system_prompt, temperature))
        if self.error:
            raise self.error
        if task.startswith("استخرج كل المعلومات"):
            return "نقطة مستخلصة [1]"
        if task.startswith("اجمع النقاط"):
            return "## ملف مجمع\n[1] نقطة."
        return self.response


def test_clean_topic_keeps_titles_that_begin_with_marifah_words() -> None:
    """عنوان مثل «معلومات عامة» لا يُقتطع لمجرد بدئه بكلمة معلومات."""
    assert _clean_topic("معلومات عامة") == "معلومات عامة"
    assert (
        _clean_topic("كل المعلومات عن درس معلومات عامة")
        == "معلومات عامة"
    )
    assert _clean_topic("معلومات درس كان وأخواتها") == "كان وأخواتها"


def test_clean_topic_strips_common_request_phrases() -> None:
    assert _clean_topic("أريد معلومات درس الخبر بالكامل") == "الخبر"
    assert _clean_topic("حضر لي معلومات درس الخبر بالكامل") == "الخبر"
    assert _clean_topic("أعطني معلومات درس الخبر") == "الخبر"
    assert (
        _clean_topic("أريد معلومات عن درس كان وأخواتها")
        == "كان وأخواتها"
    )


def test_lesson_info_node_collects_all_grades_and_cites_sources() -> None:
    sources = [
        _source(grade="أول إعدادي", text="تعريف أول إعدادي."),
        _source(grade="ثاني إعدادي", text="تفصيل ثاني إعدادي."),
    ]
    retrieval = FakeRetrieval(sources)
    model = FakeModel()
    node = create_lesson_info_node(
        call_model=model, retrieval_service=retrieval
    )

    result = asyncio.run(
        node(
            {
                "messages": ["أعطني كل المعلومات عن درس كان وأخواتها"],
                "user_role": "teacher",
                "context": {"subject": "نحو"},
                "metadata": {},
            }
        )
    )

    assert result["response"] == model.response
    assert result["lesson_topic"] == "كان وأخواتها"
    assert result["metadata"]["nodes_path"] == ["lesson_info"]
    assert result["metadata"]["lesson_info"] is True
    assert result["metadata"]["source_count"] == 2
    assert result["metadata"]["grades"] == ["أول إعدادي", "ثاني إعدادي"]
    assert result["metadata"]["response_source"] == "llm"
    assert retrieval.calls == [("كان وأخواتها", "نحو")]
    assert model.calls[0][1].startswith("أنت مساعد معلم")
    assert "**المراجع**" in model.calls[0][0]
    assert "تعريف أول إعدادي." in model.calls[0][0]
    assert "تفصيل ثاني إعدادي." in model.calls[0][0]


def test_lesson_info_node_uses_saved_topic_for_followup() -> None:
    retrieval = FakeRetrieval([_source()])
    model = FakeModel()
    node = create_lesson_info_node(
        call_model=model, retrieval_service=retrieval
    )

    result = asyncio.run(
        node(
            {
                "messages": ["أعد لي كل معلوماته"],
                "lesson_topic": "كان وأخواتها",
                "user_role": "teacher",
                "context": {},
                "metadata": {},
            }
        )
    )

    assert retrieval.calls == [("كان وأخواتها", None)]
    assert result["lesson_topic"] == "كان وأخواتها"


def test_lesson_info_node_keeps_saved_topic_without_sources() -> None:
    node = create_lesson_info_node(
        call_model=FakeModel(), retrieval_service=FakeRetrieval([])
    )

    result = asyncio.run(
        node(
            {
                "messages": ["كل معلومات هذا الدرس"],
                "lesson_topic": "كان وأخواتها",
                "user_role": "teacher",
                "context": {},
                "metadata": {},
            }
        )
    )

    assert "لم أجد مصادر" in result["response"]
    assert result["lesson_topic"] == "كان وأخواتها"
    assert result["metadata"]["response_source"] == "no_sources"
    assert result["metadata"]["source_count"] == 0


def test_lesson_info_node_keeps_requested_title_over_related_wikipedia_page() -> None:
    """صفحة ويكيبيديا القريبة لا تستبدل عنوان الدرس الذي طلبه المعلم."""
    source = _source(
        title="إن وأخواتها",
        grade="",
        text="نص عن إن وأخواتها.",
        kind="wikipedia",
        url="https://ar.wikipedia.org/wiki/إن_وأخواتها",
    )
    node = create_lesson_info_node(
        call_model=FakeModel(), retrieval_service=FakeRetrieval([source])
    )

    result = asyncio.run(
        node(
            {
                "messages": ["كل المعلومات عن درس كان وأخواتها"],
                "user_role": "teacher",
                "context": {},
                "metadata": {},
            }
        )
    )

    assert result["lesson_topic"] == "كان وأخواتها"


def test_lesson_info_node_ignores_disambiguated_wikipedia_title() -> None:
    source = _source(
        title="الخبر (السعودية)",
        grade="",
        text="الخبر مدينة سعودية.",
        kind="wikipedia",
        url="https://ar.wikipedia.org/wiki/الخبر_(السعودية)",
    )
    node = create_lesson_info_node(
        call_model=FakeModel(), retrieval_service=FakeRetrieval([source])
    )

    result = asyncio.run(
        node(
            {
                "messages": ["أريد معلومات درس الخبر"],
                "user_role": "teacher",
                "context": {"subject": "النحو"},
                "metadata": {},
            }
        )
    )

    assert result["lesson_topic"] == "الخبر"


def test_lesson_info_node_without_retrieval_does_not_call_model() -> None:
    model = FakeModel()
    node = create_lesson_info_node(call_model=model, retrieval_service=None)

    result = asyncio.run(
        node(
            {
                "messages": ["كل المعلومات عن كان وأخواتها"],
                "user_role": "teacher",
                "context": {},
                "metadata": {},
            }
        )
    )

    assert "خدمة المصادر غير متاحة" in result["response"]
    assert result["metadata"]["response_source"] == "unavailable"
    assert model.calls == []


def test_lesson_info_node_falls_back_to_sources_when_model_fails() -> None:
    node = create_lesson_info_node(
        call_model=FakeModel(error=RuntimeError("down")),
        retrieval_service=FakeRetrieval([_source()]),
    )

    result = asyncio.run(
        node(
            {
                "messages": ["معلومات درس كان وأخواتها"],
                "user_role": "teacher",
                "context": {},
                "metadata": {},
            }
        )
    )

    assert "تعذر توليف ملف الدرس" in result["response"]
    assert "كان وأخواتها أفعال ناسخة" in result["response"]
    assert result["metadata"]["response_source"] == "fallback"


def test_lesson_info_node_batches_large_sources() -> None:
    sources = [
        _source(
            title=f"مصدر {index}",
            grade="",
            text="ا" * 5000,
        )
        for index in range(1, 5)
    ]
    model = FakeModel()
    node = create_lesson_info_node(
        call_model=model, retrieval_service=FakeRetrieval(sources)
    )

    result = asyncio.run(
        node(
            {
                "messages": ["كل معلومات الدرس"],
                "lesson_topic": "كان وأخواتها",
                "user_role": "teacher",
                "context": {"subject": "نحو"},
                "metadata": {},
            }
        )
    )

    extract_calls = [
        call for call in model.calls if call[0].startswith(LESSON_INFO_EXTRACT_TASK[:20])
    ]
    compose_calls = [
        call for call in model.calls if call[0].startswith(LESSON_INFO_COMPOSE_TASK[:20])
    ]
    assert len(extract_calls) == 2
    assert len(compose_calls) == 1
    assert result["metadata"]["synthesis_calls"] == 3


def test_lesson_info_node_appends_sources_missing_from_response() -> None:
    sources = [
        _source(title="الأول", text="نص أول."),
        _source(title="الثاني", text="نص ثان.", url="https://example.test/2"),
    ]
    node = create_lesson_info_node(
        call_model=FakeModel(response="ملف بلا مراجع"),
        retrieval_service=FakeRetrieval(sources),
    )

    result = asyncio.run(
        node(
            {
                "messages": ["كل المعلومات عن الدرس"],
                "lesson_topic": "الدرس",
                "user_role": "teacher",
                "context": {},
                "metadata": {},
            }
        )
    )

    assert "**مصادر إضافية:**" in result["response"]
    assert "الأول" in result["response"]
    assert "الثاني" in result["response"]
    assert "https://example.test/2" in result["response"]
