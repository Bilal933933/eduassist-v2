"""مشرف تحضير الدرس: يقرر الوكيل التالي بناءً على الحالة."""

from typing import Literal

from langgraph.graph import END
from langgraph.types import Command

from orchestration.lesson_prep.state import SECTION_FIELDS, LessonPrepState

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


def _section_ready(state: LessonPrepState, name: str, field: str) -> bool:
    """القسم جاهز إن وُلد نصه أو سُجّل فشله؛ الفارغ الفاشل لا يُعاد بلا نهاية."""
    return bool(state.get(field)) or name in (state.get("failed_sections") or [])


def route_next(state: LessonPrepState) -> Command:
    iteration = state.get("iteration", 0)

    # التجميع النهائي ينهي الرسم حتى لو بقيت نتيجة الناقد في الحالة.
    # الفحص بوجود المفتاح لا بقيمته: المجمع قد يعيد نصًا فارغًا، فيجب ألا
    # يعيد السقف توجيهه إلى المجمع مرة أخرى بلا نهاية.
    if "final_lesson_plan" in state:
        return Command(goto=END)

    # تجاوز السقف لا ينهي الرسم بلا خطة: الأقسام المنتجة تُجمع بدل إسقاطها.
    if iteration >= MAX_ITERATIONS:
        return Command(goto="assembler", update={"iteration": iteration + 1})

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
    else:
        next_agent = "critic"
        for name, field in SECTION_FIELDS.items():
            if not _section_ready(state, name, field):
                next_agent = name
                break

    return Command(goto=next_agent, update={"iteration": iteration + 1})
