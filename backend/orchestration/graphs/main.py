"""الموجه الرئيسي: يستقبل الرسالة ويوجه لجراف المعلم أو الطالب."""

import json
from collections.abc import Awaitable, Callable
from typing import Any, Literal

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from orchestration.graphs.student import build_student_graph
from orchestration.graphs.teacher import build_teacher_graph
from orchestration.state import AgentState

RoleRoute = Literal["teacher", "student"]


def scoped_thread_id(user_id: str, conversation_id: str) -> str:
    """معرّف خيط معزول يجمع بين المستخدم والمحادثة."""
    return json.dumps(
        [user_id, conversation_id], ensure_ascii=False, separators=(",", ":")
    )


def checkpoint_config(user_id: str, conversation_id: str) -> dict:
    """عزل حالة كل محادثة داخل نطاق المستخدم."""
    return {
        "configurable": {"thread_id": scoped_thread_id(user_id, conversation_id)},
        "recursion_limit": 100,
    }


def route_role(state: AgentState) -> RoleRoute:
    """توجيه المعلم لمساره، وغيره لمسار الطالب الآمن."""
    if state.get("user_role") != "teacher":
        return "student"
    return "teacher"


def build_graph(
    checkpointer: Any | None = None,
    *,
    call_model: Callable[[str, str, float], Awaitable[str]],
    classify_intent: Callable[
        [str, tuple[str, ...]], Awaitable[str]
    ],
    retrieval_service: Any | None = None,
):
    """تجميع الموجه مع الجرافين الفرعيين ونقطة التفتيش المحقونة."""
    teacher = build_teacher_graph(
        call_model=call_model,
        classify_intent=classify_intent,
        retrieval_service=retrieval_service,
    )
    student = build_student_graph(
        call_model=call_model,
        classify_intent=classify_intent,
    )
    builder = StateGraph(AgentState)
    builder.add_node("teacher", teacher)
    builder.add_node("student", student)
    builder.add_conditional_edges(START, route_role, ["teacher", "student"])
    builder.add_edge("teacher", END)
    builder.add_edge("student", END)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())
