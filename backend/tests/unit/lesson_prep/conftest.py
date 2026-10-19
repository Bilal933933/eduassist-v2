"""التجهيزات المشتركة لاختبارات تحضير الدرس."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from orchestration.nodes.teacher.lesson_prep_node import create_lesson_prep_node

CallModel = Callable[[str, str, float], Awaitable[str]]


class FakeRetrievalService:
    """خدمة استرجاع وهمية تعيد نتائج فارغة افتراضياً."""

    def __init__(self, chunks: list[dict[str, Any]] | None = None) -> None:
        self._chunks = chunks or []

    async def search_hybrid(
        self,
        query: str,
        subject: str | None = None,
        grade: str | None = None,
    ) -> list[dict[str, Any]]:
        return self._chunks


class FakeCallModel:
    """نموذج وهمي يسجل الاستدعاءات ويعيد نصوصاً محددة."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.calls: list[tuple[str, str, float]] = []
        self.responses = responses or {}

    async def __call__(
        self, task: str, system_prompt: str, temperature: float
    ) -> str:
        self.calls.append((task, system_prompt, temperature))
        if "قيّم جودة خطة الدرس" in task:
            return self.responses.get(
                "critic", '{"score": 0.9, "section": null}'
            )
        if self.responses:
            # إرجاع الاستجابة المطابقة للنوع إن وجدت
            for key, value in self.responses.items():
                if key in task:
                    return value
        return "نتيجة تجريبية"


@pytest.fixture
def fake_retrieval_service() -> FakeRetrievalService:
    return FakeRetrievalService()


@pytest.fixture
def fake_call_model() -> FakeCallModel:
    return FakeCallModel()


@pytest.fixture
def lesson_prep_node(
    fake_call_model: FakeCallModel,
    fake_retrieval_service: FakeRetrievalService,
):
    return create_lesson_prep_node(
        call_model=fake_call_model,
        retrieval_service=fake_retrieval_service,
    )


@pytest.fixture
def base_context() -> dict[str, Any]:
    return {
        "subject": "اللغة العربية",
        "grade": "الثاني المتوسط",
        "topic": "كان وأخواتها",
    }


@pytest.fixture
def base_messages() -> list[str]:
    return ["كان وأخواتها"]
