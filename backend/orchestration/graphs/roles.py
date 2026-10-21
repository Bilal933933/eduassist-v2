"""بناء رسم الدور: مسار الطالب والمعلم من العقد نفسها."""

from collections.abc import Awaitable, Callable
from typing import Literal

from langgraph.graph import END, START, StateGraph

from orchestration.nodes.shared import (
    create_abuse_node,
    create_classification_node,
    create_general_node,
    create_greeting_node,
    create_retrieve_node,
    create_summarize_node,
    quick_reply_node,
    route_intent,
)
from orchestration.nodes.shared.classification import STUDENT_INTENTS, TEACHER_INTENTS
from orchestration.nodes.student import create_generation_node
from orchestration.nodes.teacher import (
    create_lesson_info_node,
    create_lesson_prep_node,
    create_teacher_generation_node,
)
from orchestration.state import AgentOutput, AgentState
from retrieval.service import RetrievalService

Role = Literal["student", "teacher"]


def _route_after_classify(state: AgentState) -> str:
    """التوليد يمر بالاسترجاع، وتعديل خطة سابقة يستخدم عقدة التحضير."""
    intent = route_intent(state)
    if intent == "generation":
        return "retrieve"
    if intent == "lesson_refine":
        return "lesson_prep"
    return intent


def build_role_graph(
    *,
    role: Role,
    call_model: Callable[[str, str, float], Awaitable[str]],
    classify_intent: Callable[[str, tuple[str, ...]], Awaitable[str]],
    retrieval_service: RetrievalService | None = None,
):
    """تجميع عقد الدور في رسم فرعي بلا نقاط تفتيش."""
    is_teacher = role == "teacher"
    intents = TEACHER_INTENTS if is_teacher else STUDENT_INTENTS

    builder = StateGraph(AgentState, output_schema=AgentOutput)

    builder.add_node("classify", create_classification_node(classify_intent, intents))
    builder.add_node("retrieve", create_retrieve_node(retrieval_service))
    builder.add_node("greeting", create_greeting_node(call_model))
    builder.add_node("quick_reply", quick_reply_node)
    builder.add_node(
        "generation",
        (
            create_teacher_generation_node(call_model)
            if is_teacher
            else create_generation_node(call_model)
        ),
    )
    builder.add_node("general", create_general_node(call_model))
    builder.add_node("abuse", create_abuse_node(call_model))
    builder.add_node("recall", create_summarize_node(call_model))

    targets = ["retrieve", "greeting", "quick_reply", "general", "abuse", "recall"]
    if is_teacher:
        builder.add_node(
            "lesson_prep",
            create_lesson_prep_node(
                call_model=call_model,
                retrieval_service=retrieval_service,
            ),
        )
        targets.append("lesson_prep")

        builder.add_node(
            "lesson_info",
            create_lesson_info_node(
                call_model=call_model,
                retrieval_service=retrieval_service,
            ),
        )
        targets.append("lesson_info")

    builder.add_edge(START, "classify")
    builder.add_conditional_edges("classify", _route_after_classify, targets)
    for node in ("greeting", "quick_reply", "general", "abuse", "generation"):
        builder.add_edge(node, END)
    builder.add_edge("retrieve", "generation")
    builder.add_edge("recall", "generation")
    if is_teacher:
        builder.add_edge("lesson_prep", END)
        builder.add_edge("lesson_info", END)

    return builder.compile()
