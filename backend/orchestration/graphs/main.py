"""الرسم الرئيسي للمساعد ومساراته الأولية."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from orchestration.nodes import (
    create_classification_node,
    create_generation_node,
    greeting_node,
    quick_reply_node,
    route_intent,
)
from orchestration.state import AgentState


def checkpoint_config(user_id: str, conversation_id: str) -> dict:
    """عزل حالة كل محادثة داخل نطاق المستخدم."""
    scoped_thread_id = json.dumps(
        [user_id, conversation_id], ensure_ascii=False, separators=(",", ":")
    )
    return {"configurable": {"thread_id": scoped_thread_id}}


def build_graph(
    checkpointer: Any | None = None,
    *,
    call_model: Callable[[str, str, float], Awaitable[str]],
    classify_intent: Callable[
        [str, tuple[str, ...]], Awaitable[str]
    ],
):
    """تجميع الرسم الرئيسي مع حافظ نقاط التفتيش المحقون."""
    builder = StateGraph(AgentState)
    builder.add_node("classify", create_classification_node(classify_intent))
    builder.add_node("greeting", greeting_node)
    builder.add_node("quick_reply", quick_reply_node)
    builder.add_node("generation", create_generation_node(call_model))
    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        route_intent,
        ["greeting", "quick_reply", "generation"],
    )
    builder.add_edge("greeting", END)
    builder.add_edge("quick_reply", END)
    builder.add_edge("generation", END)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())
