"""اختبارات العقد الفردية لمسار تحضير الدرس."""
from __future__ import annotations

from typing import Any

import pytest

from orchestration.lesson_prep.agents import (
    create_assembler_node,
    create_critic_node,
    create_retriever_node,
)
from orchestration.lesson_prep.state import LessonPrepState


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
async def test_critic_node_high_score() -> None:
    """يتحقق من أن عقدة الناقد تعيد نتيجة عالية عند جودة جيدة."""
    call_model = FakeCallModel(
        response='{"score": 0.9, "section": null}'
    )
    node = create_critic_node(call_model)

    state: LessonPrepState = {
        "topic": "كان وأخواتها",
        "sections": {
            "basic_info": "بيانات أساسية",
            "objectives": "أهداف تعليمية",
            "lesson_flow": "سير الدرس",
        },
        "section_2_objectives": "أهداف تعليمية للدرس",
    }

    result = await node(state)

    assert result["quality_score"] == 0.9
    assert result["needs_improvement"] == ""
    assert "critic" in result["sections"]


@pytest.mark.asyncio
async def test_critic_node_low_score_returns_section() -> None:
    """يتحقق من أن عقدة الناقد تحدد القسم الذي يحتاج تحسين عند نتيجة منخفضة."""
    call_model = FakeCallModel(
        response='{"score": 0.4, "section": "lesson_flow"}'
    )
    node = create_critic_node(call_model)

    state: LessonPrepState = {
        "topic": "كان وأخواتها",
        "sections": {
            "basic_info": "بيانات أساسية",
            "objectives": "أهداف تعليمية",
            "lesson_flow": "سير الدرس ناقص",
        },
        "section_2_objectives": "أهداف تعليمية للدرس",
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
        "sections": {},
        "section_2_objectives": "",
    }

    result = await node(state)

    assert result["quality_score"] == 0.5
    assert result["needs_improvement"] == ""


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
    assert call_model.calls[0][0].startswith("قم بتجميع كل الأقسام")


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
