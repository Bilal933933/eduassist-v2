"""حالة تحضير الدرس: مستقلة عن AgentState."""

from typing import Any

from typing_extensions import Annotated, TypedDict

import operator


def _merge_sections(
    current: dict[str, str] | None,
    update: dict[str, str] | None,
) -> dict[str, str]:
    """دمج أقسام الدرس من وكلاء متعددين دون مسح البيانات الموجودة."""
    if current is None:
        current = {}
    if update is None:
        return current
    return {**current, **update}


def _merge_metadata(
    current: dict[str, Any] | None,
    update: dict[str, Any] | None,
) -> dict[str, Any]:
    """دمج الميتا بيانات من عقد متعددة في الرسم الفرعي."""
    if current is None:
        current = {}
    if update is None:
        return current
    return {**current, **update}


class LessonPrepState(TypedDict, total=False):
    subject: str
    grade: str
    topic: str

    retrieved_chunks: list[dict[str, Any]]

    sections: Annotated[dict[str, str], _merge_sections]
    quality_score: float
    needs_improvement: str
    metadata: Annotated[dict[str, Any], _merge_metadata]
    retried_sections: Annotated[list[str], lambda a, b: (a or []) + (b or [])]

    section_1_basic: str
    section_2_objectives: str
    section_3_prior: str
    section_4_materials: str
    section_5_flow: str
    section_6_assessment: str
    section_7_homework: str
    section_8_differentiation: str
    section_9_notes: str
    final_lesson_plan: str

    iteration: int
