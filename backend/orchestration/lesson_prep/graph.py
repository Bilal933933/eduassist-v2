"""بناء الرسم الفرعي لتحضير الدرس."""

from collections.abc import Awaitable, Callable

from langgraph.graph import END, START, StateGraph

from orchestration.lesson_prep.agents import (
    create_assembler_node,
    create_assessment_node,
    create_basic_info_node,
    create_differentiation_node,
    create_homework_node,
    create_lesson_flow_node,
    create_materials_node,
    create_notes_node,
    create_objectives_node,
    create_prior_knowledge_node,
    create_retriever_node,
)
from orchestration.lesson_prep.state import LessonPrepState
from orchestration.lesson_prep.supervisor import route_next
from retrieval.service import RetrievalService

CallModel = Callable[[str, str, float], Awaitable[str]]


def build_lesson_prep_subgraph(
    *,
    call_model: CallModel,
    retrieval_service: RetrievalService | None,
):
    builder = StateGraph(LessonPrepState)

    builder.add_node("supervisor", route_next)
    builder.add_node("retriever", create_retriever_node(retrieval_service))
    builder.add_node("basic_info", create_basic_info_node(call_model))
    builder.add_node("objectives", create_objectives_node(call_model))
    builder.add_node("prior_knowledge", create_prior_knowledge_node(call_model))
    builder.add_node("materials", create_materials_node(call_model))
    builder.add_node("lesson_flow", create_lesson_flow_node(call_model))
    builder.add_node("assessment", create_assessment_node(call_model))
    builder.add_node("homework", create_homework_node(call_model))
    builder.add_node("differentiation", create_differentiation_node(call_model))
    builder.add_node("notes", create_notes_node(call_model))
    builder.add_node("assembler", create_assembler_node(call_model))

    builder.add_edge(START, "supervisor")

    for agent in [
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
        "assembler",
    ]:
        builder.add_edge(agent, "supervisor")

    return builder.compile()
