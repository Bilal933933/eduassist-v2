"""اختبارات العقد الفردية لمسار تحضير الدرس."""
from __future__ import annotations

from typing import Any

import pytest

from orchestration.lesson_prep.agents import (
    _parse_score,
    create_assembler_node,
    create_critic_node,
    create_objectives_node,
    create_retriever_node,
)
from orchestration.lesson_prep.state import LessonPrepState


class _FailingRetrievalService:
    """خدمة استرجاع تفشل عمداً لاختبار تدهور الرسم بأمان."""

    async def search_hybrid(
        self,
        query: str,
        subject: str | None = None,
        grade: str | None = None,
    ) -> list[dict[str, Any]]:
        raise RuntimeError("قاعدة المعرفة غير متاحة")


class FakeCallModel:
    def __init__(self, response: str = "نتيجة تجريبية") -> None:
        self.calls: list[tuple[str, str, float]] = []
        self.response = response

    async def __call__(
        self, task: str, system_prompt: str, temperature: float
    ) -> str:
        self.calls.append((task, system_prompt, temperature))
        return self.response


class FakeRetrievalService:
    def __init__(self, chunks: list[dict[str, Any]] | None = None) -> None:
        self._chunks = chunks or []

    async def search_hybrid(
        self,
        query: str,
        subject: str | None = None,
        grade: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._chunks


@pytest.mark.asyncio
async def test_retriever_node_returns_chunks() -> None:
    """يتحقق من أن عقدة المسترجع تعيد نتائج الاسترجاع."""
    retrieval_service = FakeRetrievalService(
        chunks=[{"text": "كان وأخواتها أفعال ناقصة", "source_type": "document"}]
    )
    node = create_retriever_node(retrieval_service)

    state: LessonPrepState = {
        "subject": "اللغة العربية",
        "grade": "الثاني المتوسط",
        "topic": "كان وأخواتها",
    }

    result = await node(state)

    assert "retrieved_chunks" in result
    assert len(result["retrieved_chunks"]) == 1
    assert result["retrieved_chunks"][0]["text"] == "كان وأخواتها أفعال ناقصة"


@pytest.mark.asyncio
async def test_retriever_node_returns_empty_when_service_none() -> None:
    """يتحقق من أن عقدة المسترجع تعيد قائمة فارغة عند عدم وجود خدمة."""
    node = create_retriever_node(retrieval_service=None)

    state: LessonPrepState = {
        "subject": "اللغة العربية",
        "grade": "الثاني المتوسط",
        "topic": "كان وأخواتها",
    }

    result = await node(state)

    assert result["retrieved_chunks"] == []


@pytest.mark.asyncio
async def test_objectives_node_passes_retrieved_content_to_prompt() -> None:
    """يتحقق من أن محتوى الاسترجاع الحقيقي يصل إلى موجّه الوكيل."""
    call_model = FakeCallModel(response="أهداف تعليمية")
    node = create_objectives_node(call_model)

    state: LessonPrepState = {
        "topic": "كان وأخواتها",
        "retrieved_chunks": [
            {
                "content": "كان وأخواتها أفعال ناقصة تدخل على الجملة الاسمية",
                "source_type": "curriculum",
            },
            {
                "snippet": "الأفعال الناقصة تفيد في زمن المضارع",
                "source_type": "wikipedia",
            },
        ],
    }

    await node(state)

    prompt = call_model.calls[0][0]
    assert "كان وأخواتها أفعال ناقصة تدخل على الجملة الاسمية" in prompt
    assert "الأفعال الناقصة تفيد في زمن المضارع" in prompt


@pytest.mark.asyncio
async def test_retriever_node_survives_retrieval_failure() -> None:
    """يتحقق من أن فشل الاسترجاع لا يوقف التحضير."""
    node = create_retriever_node(_FailingRetrievalService())

    state: LessonPrepState = {
        "subject": "اللغة العربية",
        "grade": "الثاني المتوسط",
        "topic": "كان وأخواتها",
    }

    result = await node(state)

    assert result["retrieved_chunks"] == []


@pytest.mark.asyncio
async def test_critic_node_high_score() -> None:
    """يتحقق من أن عقدة الناقد تعيد نتيجة عالية عند جودة جيدة."""
    call_model = FakeCallModel(
        response='{"score": 0.9, "section": null}'
    )
    node = create_critic_node(call_model)

    state: LessonPrepState = {
        "topic": "كان وأخواتها",
        "section_1_basic": "بيانات أساسية",
        "section_2_objectives": "أهداف تعليمية للدرس",
        "section_5_flow": "سير الدرس",
    }

    result = await node(state)

    assert result["quality_score"] == 0.9
    assert result["needs_improvement"] == ""
    assert "sections" not in result
    assert "بيانات أساسية" in call_model.calls[0][0]


@pytest.mark.asyncio
async def test_critic_node_low_score_returns_section() -> None:
    """يتحقق من أن عقدة الناقد تحدد القسم الذي يحتاج تحسين عند نتيجة منخفضة."""
    call_model = FakeCallModel(
        response='{"score": 0.4, "section": "lesson_flow"}'
    )
    node = create_critic_node(call_model)

    state: LessonPrepState = {
        "topic": "كان وأخواتها",
        "section_1_basic": "بيانات أساسية",
        "section_2_objectives": "أهداف تعليمية للدرس",
        "section_5_flow": "سير الدرس ناقص",
    }

    result = await node(state)

    assert result["quality_score"] == 0.4
    assert result["needs_improvement"] == "lesson_flow"


@pytest.mark.asyncio
async def test_critic_node_invalid_json_defaults() -> None:
    """يتحقق من أن عقدة الناقد تتعامل مع استجابة غير صالحةJSON."""
    call_model = FakeCallModel(response="هذا ليس JSON")
    node = create_critic_node(call_model)

    state: LessonPrepState = {
        "topic": "كان وأخواتها",
        "section_2_objectives": "",
    }

    result = await node(state)

    assert result["quality_score"] == 0.5
    assert result["needs_improvement"] == ""


@pytest.mark.asyncio
async def test_critic_node_parses_fenced_json() -> None:
    """يتحقق من أن الناقد يحلل JSON الملفوف بأسوار الماركداون."""
    call_model = FakeCallModel(
        response='```json\n{"score": 0.95, "section": null}\n```'
    )
    node = create_critic_node(call_model)

    state: LessonPrepState = {
        "topic": "كان وأخواتها",
        "section_2_objectives": "أهداف تعليمية للدرس",
        "section_3_prior": "خبرات سابقة",
    }

    result = await node(state)

    assert result["quality_score"] == 0.95
    assert result["needs_improvement"] == ""


@pytest.mark.asyncio
async def test_critic_node_ignores_unknown_section() -> None:
    """يتحقق من أن الناقد يتجاهل اسم قسم غير معروف."""
    call_model = FakeCallModel(
        response='{"score": 0.4, "section": "unknown_section"}'
    )
    node = create_critic_node(call_model)

    state: LessonPrepState = {
        "topic": "كان وأخواتها",
        "section_2_objectives": "أهداف تعليمية للدرس",
        "section_5_flow": "سير الدرس ناقص",
    }

    result = await node(state)

    assert result["quality_score"] == 0.4
    assert result["needs_improvement"] == ""


@pytest.mark.asyncio
async def test_critic_node_clamps_score_range() -> None:
    """يتحقق من أن الناقد يحدّ النتيجة ضمن المجال بين الصفر والواحد."""
    call_model = FakeCallModel(response='{"score": 5, "section": null}')
    node = create_critic_node(call_model)

    state: LessonPrepState = {
        "topic": "كان وأخواتها",
        "section_2_objectives": "",
    }

    result = await node(state)

    assert result["quality_score"] == 1.0


def test_parse_score_rejects_bool() -> None:
    """القيمة المنطقية ليست تقييمًا صالحًا ولا تُحوَّل إلى 1.0."""
    assert _parse_score(True) == 0.5
    assert _parse_score(False) == 0.5


@pytest.mark.asyncio
async def test_assembler_node_combines_sections() -> None:
    """يتحقق من أن عقدة المجمع تجمع جميع أقسام الدرس."""
    call_model = FakeCallModel(response="خطة درس نهائية")
    node = create_assembler_node(call_model)

    state: LessonPrepState = {
        "topic": "كان وأخواتها",
        "section_1_basic": "بيانات أساسية",
        "section_2_objectives": "أهداف تعليمية",
        "section_3_prior": "خبرات سابقة",
        "section_4_materials": "وسائل تعليمية",
        "section_5_flow": "سير الدرس",
        "section_6_assessment": "تقويم",
        "section_7_homework": "واجبات",
        "section_8_differentiation": "مراعاة فروق فردية",
        "section_9_notes": "ملاحظات",
    }

    result = await node(state)

    assert result["final_lesson_plan"] == "خطة درس نهائية"
    assert result["metadata"]["assembler_node"] == "assembler_node"
    assert result["metadata"]["nodes_path"] == ["assembler"]
    assert "خطة درس نهائية" in call_model.calls[0][0]
    assert "كان وأخواتها" in call_model.calls[0][0]


@pytest.mark.asyncio
async def test_assembler_node_handles_missing_sections() -> None:
    """يتحقق من أن عقدة المجمع تعمل حتى مع فقدان بعض الأقسام."""
    call_model = FakeCallModel(response="خطة درس جزئية")
    node = create_assembler_node(call_model)

    state: LessonPrepState = {
        "topic": "كان وأخواتها",
        "section_1_basic": "بيانات أساسية فقط",
    }

    result = await node(state)

    assert result["final_lesson_plan"] == "خطة درس جزئية"
