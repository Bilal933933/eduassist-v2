"""مسار المعلم: نفس عقد الطالب مع توليد مخصص لسياق المعلم."""

from collections.abc import Awaitable, Callable

from langgraph.graph import END, START, StateGraph

from orchestration.nodes.shared import (
    create_abuse_node,
    create_classification_node,
    create_general_node,
    create_greeting_node,
    create_summarize_node,
    quick_reply_node,
    route_intent,
)
from orchestration.nodes.teacher import create_teacher_generation_node
from orchestration.state import AgentState


def build_teacher_graph(
    *,
    call_model: Callable[[str, str, float], Awaitable[str]],
    classify_intent: Callable[[str, tuple[str, ...]], Awaitable[str]],
):
    """تجميع عقد مسار المعلم في رسم فرعي بلا نقاط تفتيش."""
    builder = StateGraph(AgentState)

    builder.add_node("classify", create_classification_node(classify_intent))
    builder.add_node("greeting", create_greeting_node(call_model))
    builder.add_node("quick_reply", quick_reply_node)
    builder.add_node("generation", create_teacher_generation_node(call_model))
    builder.add_node("general", create_general_node(call_model))
    builder.add_node("abuse", create_abuse_node(call_model))
    builder.add_node("recall", create_summarize_node(call_model))

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_intent,
        ["greeting", "quick_reply", "generation", "general", "abuse", "recall"],
    )
    builder.add_edge("greeting", END)
    builder.add_edge("quick_reply", END)
    builder.add_edge("generation", END)
    builder.add_edge("general", END)
    builder.add_edge("abuse", END)
    builder.add_edge("recall", "generation")

    return builder.compile()
