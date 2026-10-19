"""عوامل الوكلاء الفرعيين لتحضير الدرس."""

from collections.abc import Awaitable, Callable, Sequence
from typing import Any

from orchestration.lesson_prep.prompts import (
    ASSESSMENT_TASK,
    ASSEMBLER_TASK,
    BASIC_INFO_TASK,
    CRITIC_TASK,
    DIFFERENTIATION_TASK,
    HOMEWORK_TASK,
    LESSON_FLOW_TASK,
    MATERIALS_TASK,
    NOTES_TASK,
    OBJECTIVES_TASK,
    PRIOR_KNOWLEDGE_TASK,
)
from orchestration.lesson_prep.state import LessonPrepState
from retrieval.service import RetrievalService

CallModel = Callable[[str, str, float], Awaitable[str]]


def _format_chunks(chunks: Sequence[dict[str, Any]]) -> str:
    return "\n".join(
        f"- [{c.get('source_type', 'unknown')}] {c.get('text', '')}"
        for c in chunks
    )


def create_retriever_node(
    retrieval_service: RetrievalService | None,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def retriever_node(state: LessonPrepState) -> dict[str, Any]:
        if retrieval_service is None:
            return {"retrieved_chunks": []}
        chunks = await retrieval_service.search_hybrid(
            query=f"{state['subject']} {state['grade']} {state['topic']}",
            subject=state.get("subject"),
            grade=state.get("grade"),
        )
        return {"retrieved_chunks": chunks}

    return retriever_node


def create_basic_info_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def basic_info_node(state: LessonPrepState) -> dict[str, Any]:
        task = BASIC_INFO_TASK.format(
            subject=state["subject"],
            grade=state["grade"],
            topic=state["topic"],
        )
        result = await call_model(task, "", 0.2)
        return {"section_1_basic": result, "sections": {"basic_info": result}}

    return basic_info_node


def create_objectives_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def objectives_node(state: LessonPrepState) -> dict[str, Any]:
        task = OBJECTIVES_TASK.format(
            topic=state["topic"],
            chunks=_format_chunks(state.get("retrieved_chunks", [])),
        )
        result = await call_model(task, "", 0.3)
        return {"section_2_objectives": result, "sections": {"objectives": result}}

    return objectives_node


def create_prior_knowledge_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def prior_knowledge_node(state: LessonPrepState) -> dict[str, Any]:
        task = PRIOR_KNOWLEDGE_TASK.format(
            topic=state["topic"],
            chunks=_format_chunks(state.get("retrieved_chunks", [])),
        )
        result = await call_model(task, "", 0.3)
        return {"section_3_prior": result, "sections": {"prior_knowledge": result}}

    return prior_knowledge_node


def create_materials_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def materials_node(state: LessonPrepState) -> dict[str, Any]:
        task = MATERIALS_TASK.format(
            topic=state["topic"],
            chunks=_format_chunks(state.get("retrieved_chunks", [])),
        )
        result = await call_model(task, "", 0.3)
        return {"section_4_materials": result, "sections": {"materials": result}}

    return materials_node


def create_lesson_flow_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def lesson_flow_node(state: LessonPrepState) -> dict[str, Any]:
        task = LESSON_FLOW_TASK.format(
            topic=state["topic"],
            objectives=state.get("section_2_objectives", ""),
        )
        result = await call_model(task, "", 0.3)
        return {"section_5_flow": result, "sections": {"lesson_flow": result}}

    return lesson_flow_node


def create_assessment_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def assessment_node(state: LessonPrepState) -> dict[str, Any]:
        task = ASSESSMENT_TASK.format(
            topic=state["topic"],
            objectives=state.get("section_2_objectives", ""),
        )
        result = await call_model(task, "", 0.3)
        return {"section_6_assessment": result, "sections": {"assessment": result}}

    return assessment_node


def create_homework_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def homework_node(state: LessonPrepState) -> dict[str, Any]:
        task = HOMEWORK_TASK.format(
            topic=state["topic"],
            objectives=state.get("section_2_objectives", ""),
        )
        result = await call_model(task, "", 0.3)
        return {"section_7_homework": result, "sections": {"homework": result}}

    return homework_node


def create_differentiation_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def differentiation_node(state: LessonPrepState) -> dict[str, Any]:
        task = DIFFERENTIATION_TASK.format(
            topic=state["topic"],
            objectives=state.get("section_2_objectives", ""),
        )
        result = await call_model(task, "", 0.3)
        return {"section_8_differentiation": result, "sections": {"differentiation": result}}

    return differentiation_node


def create_notes_node(
    call_model: CallModel,
) -> Callable[[LessonPrepState], Awaitable[dict[str, Any]]]:
    async def notes_node(state: LessonPrepState) -> dict[str, Any]:
        result = await call_model(NOTES_TASK, "", 0.2)
        return {
            "section_9_notes": result,
            "sections": {"notes": result},
        }

    return notes_node


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

        # erwarج النموذج بإرجاع JSON بسيط: {"score": 0.0-1.0, "section": "القسم الذي يحتاج تحسين" أو null}
        import json

        try:
            parsed = json.loads(result)
            score = float(parsed.get("score", 0.5))
            section = parsed.get("section")
        except (json.JSONDecodeError, ValueError, TypeError):
            score = 0.5
            section = None

        return {
            "quality_score": score,
            "needs_improvement": section or "",
            "sections": {"critic": result},
            "metadata": {
                "critic_node": "critic_node",
                "quality_score": score,
                "section_needs_improvement": section or "",
            },
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
            "metadata": {
                "assembler_node": "assembler_node",
                "final_plan_generated": True,
            },
        }

    return assembler_node
