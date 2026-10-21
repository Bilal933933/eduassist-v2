"""حالة تحضير الدرس: مستقلة عن AgentState."""

from typing import Any

from typing_extensions import Annotated, TypedDict

# خريطة اسم القسم إلى حقل حالته: مصدر واحد يقرأ منه المشرف والناقد والجسر.
SECTION_FIELDS: dict[str, str] = {
    "basic_info": "section_1_basic",
    "objectives": "section_2_objectives",
    "prior_knowledge": "section_3_prior",
    "materials": "section_4_materials",
    "lesson_flow": "section_5_flow",
    "assessment": "section_6_assessment",
    "homework": "section_7_homework",
    "differentiation": "section_8_differentiation",
    "notes": "section_9_notes",
}

# التسميات العربية تُستخدم في موجّه تحديد نطاق التعديل.
SECTION_LABELS: dict[str, str] = {
    "basic_info": "البيانات الأساسية",
    "objectives": "الأهداف التعليمية",
    "prior_knowledge": "الخبرات السابقة",
    "materials": "الوسائل والمواد التعليمية",
    "lesson_flow": "سير الدرس",
    "assessment": "التقويم",
    "homework": "الواجبات والأنشطة الإثرائية",
    "differentiation": "مراعاة الفروق الفردية",
    "notes": "ملاحظات ما بعد الدرس",
}


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


def _append_list(
    current: list[str] | None,
    update: list[str] | None,
) -> list[str]:
    """إلحاق عناصر قائمة من عقد متعددة دون فقد السابق."""
    return (current or []) + (update or [])


class LessonPrepState(TypedDict, total=False):
    subject: str
    grade: str
    topic: str
    # وضع التعديل: طلب المعلم والخطة السابقة تُحقنان في موجّه كل قسم.
    request: str
    previous_plan: str

    retrieved_chunks: list[dict[str, Any]]

    quality_score: float
    needs_improvement: str
    metadata: Annotated[dict[str, Any], _merge_metadata]
    retried_sections: Annotated[list[str], _append_list]
    failed_sections: Annotated[list[str], _append_list]

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
