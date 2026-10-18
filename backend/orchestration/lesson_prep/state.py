"""حالة تحضير الدرس: مستقلة عن AgentState."""

from typing import Any

from typing_extensions import TypedDict


class LessonPrepState(TypedDict, total=False):
    subject: str
    grade: str
    topic: str

    retrieved_chunks: list[dict[str, Any]]

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
