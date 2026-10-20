"""مشرف تحضير الدرس: يقرر الوكيل التالي بناءً على الحالة."""

from typing import Literal

from langgraph.graph import END
from langgraph.types import Command

from orchestration.lesson_prep.state import LessonPrepState

# سقف زيارات المشرف: المسار السليم 13 زيارة، وكل قسم يُعاد مرة واحدة
# يضيف زيارتين (إعادة التوجيه ثم التقييم) → 32 زيارة في أسوأ الحالات.
MAX_ITERATIONS = 40
QUALITY_THRESHOLD = 0.7
MAX_RETRIES_PER_SECTION = 1

AgentName = Literal[
    "retriever",
    "basic_info",
    "objectives",
    "prior_knowledge",
    "materials",
    "lesson_flow",
    "assessment",
    "homework",
    "differentiation",
    "notes",
    "critic",
    "assembler",
]

# الأقسام التي يجوز للناقد إعادة كتابتها؛ أي قيمة أخرى تُوجَّه للتجميع.
SECTION_AGENTS = frozenset(
    {
        "basic_info",
        "objectives",
        "prior_knowledge",
        "materials",
        "lesson_flow",
        "assessment",
        "homework",
        "differentiation",
        "notes",
    }
)


def route_next(state: LessonPrepState) -> Command:
    iteration = state.get("iteration", 0)
    if iteration >= MAX_ITERATIONS:
        return Command(goto=END)

    # التجميع النهائي ينهي الرسم حتى لو بقيت نتيجة الناقد في الحالة.
    if state.get("final_lesson_plan"):
        return Command(goto=END)

    quality_score = state.get("quality_score")
    needs_improvement = state.get("needs_improvement")

    # الناقد قام بتقييم الخطة
    if quality_score is not None:
        retried = state.get("retried_sections", [])
        can_retry = (
            quality_score < QUALITY_THRESHOLD
            and needs_improvement in SECTION_AGENTS
            and needs_improvement not in retried
        )
        if can_retry:
            # جودة منخفضة: ارجع للقسم الذي يحتاج تحسين، واعيد تعيين التقييم
            return Command(
                goto=needs_improvement,
                update={
                    "iteration": iteration + 1,
                    "quality_score": None,
                    "needs_improvement": "",
                    "retried_sections": [needs_improvement],
                },
            )
        # جودة مقبولة أو قسم غير صالح أو أُعيدت كتابته: انتقل للتجميع النهائي
        return Command(
            goto="assembler",
            update={
                "iteration": iteration + 1,
                "quality_score": None,
                "needs_improvement": "",
            },
        )

    # التسلسل الطبيعي عند اكتمال الأقسام
    if "retrieved_chunks" not in state:
        next_agent = "retriever"
    elif not state.get("section_1_basic"):
        next_agent = "basic_info"
    elif not state.get("section_2_objectives"):
        next_agent = "objectives"
    elif not state.get("section_3_prior"):
        next_agent = "prior_knowledge"
    elif not state.get("section_4_materials"):
        next_agent = "materials"
    elif not state.get("section_5_flow"):
        next_agent = "lesson_flow"
    elif not state.get("section_6_assessment"):
        next_agent = "assessment"
    elif not state.get("section_7_homework"):
        next_agent = "homework"
    elif not state.get("section_8_differentiation"):
        next_agent = "differentiation"
    elif not state.get("section_9_notes"):
        next_agent = "notes"
    elif not state.get("final_lesson_plan"):
        next_agent = "critic"
    else:
        next_agent = END

    return Command(goto=next_agent, update={"iteration": iteration + 1})
