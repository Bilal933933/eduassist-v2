"""عوامل الوكلاء الفرعيين لتحضير الدرس."""

import logging
from collections.abc import Awaitable, Callable, Sequence
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
from orchestration.lesson_prep.state import LessonPrepState
from orchestration.lesson_prep.supervisor import SECTION_AGENTS
from orchestration.state import append_node
from retrieval.service import RetrievalService
from shared.json_parser import extract_json_object

CallModel = Callable[[str, str, float], Awaitable[str]]

logger = logging.getLogger("eduassist.lesson_prep.agents")

# نتيجة بديلة عند تعذّر قراءة تقييم الناقد، فلا يُبنى قرار على قيمة مختلقة.
DEFAULT_QUALITY_SCORE = 0.5


def _format_chunks(chunks: Sequence[dict[str, Any]]) -> str:
    """تنسيق نتائج الاسترجاع بنص يُمرَّر إلى الوكلاء.

    نتائج المنهج تحمل المفتاح ``content`` ونتائج ويكيبيديا ``snippet``،
    فيُقرأ الاثنان حتى لا يصل الوكيل محتوى فارغاً.
    """
    lines: list[str] = []
    for chunk in chunks:
        body = chunk.get("content") or chunk.get("snippet") or chunk.get("text") or ""
        if not str(body).strip():
            continue
        lines.append(f"- [{chunk.get('source_type', 'unknown')}] {body}")
    return "\n".join(lines)


def _with_node(
    state: LessonPrepState,
    node_name: str,
    update: dict[str, Any],
) -> dict[str, Any]:
    """إضافة اسم العقدة إلى مسار التنفيذ مع تحديثات العقدة."""
    return {
        **update,
        "metadata": append_node(state.get("metadata"), node_name),
    }


def create_retriever_node(
    retrieval_service: RetrievalService | None,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def retriever_node(state: LessonPrepState) -> dict[str, Any]:
        if retrieval_service is None:
            return _with_node(state, "retriever", {"retrieved_chunks": []})
        try:
            chunks = await retrieval_service.search_hybrid(
                query=f"{state['subject']} {state['grade']} {state['topic']}",
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
            rule=FORMAT_RULE,
        )
        result = await call_model(task, "", 0.2)
        return _with_node(
            state,
            "basic_info",
            {"section_1_basic": result, "sections": {"basic_info": result}},
        )

    return basic_info_node


def create_objectives_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def objectives_node(state: LessonPrepState) -> dict[str, Any]:
        task = OBJECTIVES_TASK.format(
            topic=state["topic"],
            chunks=_format_chunks(state.get("retrieved_chunks", [])),
            rule=FORMAT_RULE,
        )
        result = await call_model(task, "", 0.3)
        return _with_node(
            state,
            "objectives",
            {"section_2_objectives": result, "sections": {"objectives": result}},
        )

    return objectives_node


def create_prior_knowledge_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def prior_knowledge_node(state: LessonPrepState) -> dict[str, Any]:
        task = PRIOR_KNOWLEDGE_TASK.format(
            topic=state["topic"],
            chunks=_format_chunks(state.get("retrieved_chunks", [])),
            rule=FORMAT_RULE,
        )
        result = await call_model(task, "", 0.3)
        return _with_node(
            state,
            "prior_knowledge",
            {
                "section_3_prior": result,
                "sections": {"prior_knowledge": result},
            },
        )

    return prior_knowledge_node


def create_materials_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def materials_node(state: LessonPrepState) -> dict[str, Any]:
        task = MATERIALS_TASK.format(
            topic=state["topic"],
            chunks=_format_chunks(state.get("retrieved_chunks", [])),
            rule=FORMAT_RULE,
        )
        result = await call_model(task, "", 0.3)
        return _with_node(
            state,
            "materials",
            {"section_4_materials": result, "sections": {"materials": result}},
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
        result = await call_model(task, "", 0.3)
        return _with_node(
            state,
            "lesson_flow",
            {"section_5_flow": result, "sections": {"lesson_flow": result}},
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
        result = await call_model(task, "", 0.3)
        return _with_node(
            state,
            "assessment",
            {"section_6_assessment": result, "sections": {"assessment": result}},
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
        result = await call_model(task, "", 0.3)
        return _with_node(
            state,
            "homework",
            {"section_7_homework": result, "sections": {"homework": result}},
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
        result = await call_model(task, "", 0.3)
        return _with_node(
            state,
            "differentiation",
            {
                "section_8_differentiation": result,
                "sections": {"differentiation": result},
            },
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
        result = await call_model(task, "", 0.2)
        return _with_node(
            state,
            "notes",
            {
                "section_9_notes": result,
                "sections": {"notes": result},
            },
        )

    return notes_node


def _parse_score(value: Any) -> float:
    """قراءة نتيجة الجودة وتقييدها بين الصفر والواحد."""
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


def create_critic_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def critic_node(state: LessonPrepState) -> dict[str, Any]:
        task = CRITIC_TASK.format(
            topic=state["topic"],
            sections="\n\n".join(
                f"## {k}\n{v}" for k, v in state.get("sections", {}).items()
            ),
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
            "sections": {"critic": result},
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
