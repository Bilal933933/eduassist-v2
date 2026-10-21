"""عوامل الوكلاء الفرعيين لتحضير الدرس."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from orchestration.lesson_prep.prompts import (
    ASSESSMENT_TASK,
    ASSEMBLER_TASK,
    BASIC_INFO_TASK,
    CRITIC_TASK,
    DIFFERENTIATION_TASK,
    FORMAT_RULE,
    HOMEWORK_TASK,
    LESSON_FLOW_TASK,
    MATERIALS_TASK,
    NOTES_TASK,
    OBJECTIVES_TASK,
    PRIOR_KNOWLEDGE_TASK,
)
from orchestration.lesson_prep.state import SECTION_FIELDS, LessonPrepState
from orchestration.lesson_prep.supervisor import SECTION_AGENTS
from orchestration.nodes.shared.retrieval import format_chunks
from orchestration.state import append_node
from retrieval.service import RetrievalService
from shared.json_parser import extract_json_object

CallModel = Callable[[str, str, float], Awaitable[str]]

logger = logging.getLogger("eduassist.lesson_prep.agents")

# نتيجة بديلة عند تعذّر قراءة تقييم الناقد، فلا يُبنى قرار على قيمة مختلقة.
DEFAULT_QUALITY_SCORE = 0.5


def _with_node(
    state: LessonPrepState,
    node_name: str,
    update: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    """إضافة اسم العقدة إلى مسار التنفيذ مع تحديثات العقدة."""
    return {
        **update,
        "metadata": append_node(state.get("metadata"), node_name, **extra),
    }


def _refinement_suffix(state: LessonPrepState) -> str:
    """سياق التعديل: يُلحق بموجّه القسم عند تحضير سابق يُعاد صياغته."""
    plan = state.get("previous_plan") or ""
    request = state.get("request") or ""
    if not plan:
        return ""
    return (
        "\n\nهذه إعادة صياغة لخطة سابقة."
        f"\nالخطة السابقة:\n{plan}"
        f"\n\nطلب المعلم: {request}"
        "\nعدّل هذا القسم بما يحقق الطلب مع الحفاظ على ما لم يطلبه التعديل."
    )


async def _generate_section(
    call_model: CallModel,
    *,
    task: str,
    node_name: str,
    field: str,
    state: LessonPrepState,
    temperature: float,
) -> dict[str, Any]:
    """توليد قسم واحد: فشل نداء واحد يُعلَّم ويُتخطى بدل إسقاط التحضير."""
    try:
        result = await call_model(task, "", temperature)
    except Exception as error:
        logger.warning("فشل توليد قسم %s: %s", node_name, error)
        return _with_node(
            state,
            node_name,
            {field: "", "failed_sections": [node_name]},
            section_failed=True,
        )
    return _with_node(state, node_name, {field: result})


def create_retriever_node(
    retrieval_service: RetrievalService | None,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def retriever_node(state: LessonPrepState) -> dict[str, Any]:
        if retrieval_service is None:
            return _with_node(state, "retriever", {"retrieved_chunks": []})
        try:
            chunks = await retrieval_service.search_hybrid(
                query=(
                    f"{state['subject']} {state['grade']} "
                    f"{state['topic']} {state.get('request', '')}"
                ),
                subject=state.get("subject"),
                grade=state.get("grade"),
            )
        except Exception as error:
            # فشل الاسترجاع لا يوقف التحضير: يكمل الوكيل بلا محتوى مرجعي.
            logger.warning("تعذر الاسترجاع أثناء تحضير الدرس: %s", error)
            chunks = []
        return _with_node(state, "retriever", {"retrieved_chunks": chunks})

    return retriever_node


def create_basic_info_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def basic_info_node(state: LessonPrepState) -> dict[str, Any]:
        task = BASIC_INFO_TASK.format(
            subject=state.get("subject") or "غير محدد",
            grade=state.get("grade") or "غير محدد",
            topic=state["topic"],
            duration=state.get("duration_minutes") or 45,
            rule=FORMAT_RULE,
        )
        return await _generate_section(
            call_model,
            task=task + _refinement_suffix(state),
            node_name="basic_info",
            field="section_1_basic",
            state=state,
            temperature=0.2,
        )

    return basic_info_node


def create_objectives_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def objectives_node(state: LessonPrepState) -> dict[str, Any]:
        task = OBJECTIVES_TASK.format(
            topic=state["topic"],
            chunks=format_chunks(state.get("retrieved_chunks", [])),
            rule=FORMAT_RULE,
        )
        return await _generate_section(
            call_model,
            task=task + _refinement_suffix(state),
            node_name="objectives",
            field="section_2_objectives",
            state=state,
            temperature=0.3,
        )

    return objectives_node


def create_prior_knowledge_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def prior_knowledge_node(state: LessonPrepState) -> dict[str, Any]:
        task = PRIOR_KNOWLEDGE_TASK.format(
            topic=state["topic"],
            chunks=format_chunks(state.get("retrieved_chunks", [])),
            rule=FORMAT_RULE,
        )
        return await _generate_section(
            call_model,
            task=task + _refinement_suffix(state),
            node_name="prior_knowledge",
            field="section_3_prior",
            state=state,
            temperature=0.3,
        )

    return prior_knowledge_node


def create_materials_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def materials_node(state: LessonPrepState) -> dict[str, Any]:
        task = MATERIALS_TASK.format(
            topic=state["topic"],
            chunks=format_chunks(state.get("retrieved_chunks", [])),
            rule=FORMAT_RULE,
        )
        return await _generate_section(
            call_model,
            task=task + _refinement_suffix(state),
            node_name="materials",
            field="section_4_materials",
            state=state,
            temperature=0.3,
        )

    return materials_node


def create_lesson_flow_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def lesson_flow_node(state: LessonPrepState) -> dict[str, Any]:
        task = LESSON_FLOW_TASK.format(
            topic=state["topic"],
            objectives=state.get("section_2_objectives", ""),
            rule=FORMAT_RULE,
        )
        return await _generate_section(
            call_model,
            task=task + _refinement_suffix(state),
            node_name="lesson_flow",
            field="section_5_flow",
            state=state,
            temperature=0.3,
        )

    return lesson_flow_node


def create_assessment_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def assessment_node(state: LessonPrepState) -> dict[str, Any]:
        task = ASSESSMENT_TASK.format(
            topic=state["topic"],
            objectives=state.get("section_2_objectives", ""),
            rule=FORMAT_RULE,
        )
        return await _generate_section(
            call_model,
            task=task + _refinement_suffix(state),
            node_name="assessment",
            field="section_6_assessment",
            state=state,
            temperature=0.3,
        )

    return assessment_node


def create_homework_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def homework_node(state: LessonPrepState) -> dict[str, Any]:
        task = HOMEWORK_TASK.format(
            topic=state["topic"],
            objectives=state.get("section_2_objectives", ""),
            rule=FORMAT_RULE,
        )
        return await _generate_section(
            call_model,
            task=task + _refinement_suffix(state),
            node_name="homework",
            field="section_7_homework",
            state=state,
            temperature=0.3,
        )

    return homework_node


def create_differentiation_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def differentiation_node(state: LessonPrepState) -> dict[str, Any]:
        task = DIFFERENTIATION_TASK.format(
            topic=state["topic"],
            objectives=state.get("section_2_objectives", ""),
            rule=FORMAT_RULE,
        )
        return await _generate_section(
            call_model,
            task=task + _refinement_suffix(state),
            node_name="differentiation",
            field="section_8_differentiation",
            state=state,
            temperature=0.3,
        )

    return differentiation_node


def create_notes_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def notes_node(state: LessonPrepState) -> dict[str, Any]:
        task = NOTES_TASK.format(
            topic=state["topic"],
            rule=FORMAT_RULE,
        )
        return await _generate_section(
            call_model,
            task=task + _refinement_suffix(state),
            node_name="notes",
            field="section_9_notes",
            state=state,
            temperature=0.2,
        )

    return notes_node


def _parse_score(value: Any) -> float:
    """قراءة نتيجة الجودة وتقييدها بين الصفر والواحد."""
    if isinstance(value, bool):
        return DEFAULT_QUALITY_SCORE
    try:
        score = float(value)
    except (TypeError, ValueError):
        return DEFAULT_QUALITY_SCORE
    return min(max(score, 0.0), 1.0)


def _parse_section(value: Any) -> str:
    """قراءة القسم المطلوب تحسينه والتأكد أنه قسم يعرفه المشرف."""
    if not isinstance(value, str) or value not in SECTION_AGENTS:
        return ""
    return value


def _sections_view(state: LessonPrepState) -> str:
    """عرض أقسام الخطة للناقد من الحقول المصدرية وحدها."""
    return "\n\n".join(
        f"## {name}\n{state.get(field) or 'غير متوفر.'}"
        for name, field in SECTION_FIELDS.items()
    )


def create_critic_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def critic_node(state: LessonPrepState) -> dict[str, Any]:
        task = CRITIC_TASK.format(
            topic=state["topic"],
            sections=_sections_view(state),
            objectives=state.get("section_2_objectives", ""),
        )
        result = await call_model(task, "", 0.3)

        # النماذج تلفّ JSON بأسوار الماركداون أحياناً، فيُستخرج الكائن منها.
        verdict = extract_json_object(result) or {}
        score = _parse_score(verdict.get("score"))
        section = _parse_section(verdict.get("section"))

        return {
            "quality_score": score,
            "needs_improvement": section or "",
            "metadata": append_node(
                state.get("metadata"),
                "critic",
                critic_node="critic_node",
                quality_score=score,
                section_needs_improvement=section or "",
            ),
        }

    return critic_node


def create_assembler_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def assembler_node(state: LessonPrepState) -> dict[str, Any]:
        task = ASSEMBLER_TASK.format(
            topic=state["topic"],
            section_1=state.get("section_1_basic", ""),
            section_2=state.get("section_2_objectives", ""),
            section_3=state.get("section_3_prior", ""),
            section_4=state.get("section_4_materials", ""),
            section_5=state.get("section_5_flow", ""),
            section_6=state.get("section_6_assessment", ""),
            section_7=state.get("section_7_homework", ""),
            section_8=state.get("section_8_differentiation", ""),
            section_9=state.get("section_9_notes", ""),
        )
        result = await call_model(task, "", 0.2)
        return {
            "final_lesson_plan": result,
            "metadata": append_node(
                state.get("metadata"),
                "assembler",
                assembler_node="assembler_node",
                final_plan_generated=True,
            ),
        }

    return assembler_node
