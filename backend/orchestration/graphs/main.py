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


def checkpoint_config(user_id: str, conversation_id: str) -> dict:
    """عزل حالة كل محادثة داخل نطاق المستخدم."""
    scoped_thread_id = json.dumps(
        [user_id, conversation_id], ensure_ascii=False, separators=(",", ":")
    )
    return {"configurable": {"thread_id": scoped_thread_id}}


def route_role(state: dict) -> RoleRoute:
    """توجيه المعلم ذي البروفايل لمساره، وغيره لمسار الطالب الآمن."""
    # بلا تعليق AgentState عمدًا: لانغ غراف يستنتج مخطط الدخل من التعليق
    # فيقرأ من نقطة التفتيش الفارغة أول مرة بدل دمج المدخلات.
    if state.get("user_role") != "teacher":
        return "student"
    brief = state.get("context", {}).get("teacher_brief", "")
    return "teacher" if brief else "student"


def build_graph(
    checkpointer: Any | None = None,
    *,
    call_model: Callable[[str, str, float], Awaitable[str]],
    classify_intent: Callable[
        [str, tuple[str, ...]], Awaitable[str]
    ],
):
    """تجميع الموجه مع الجرافين الفرعيين ونقطة التفتيش المحقونة."""
    teacher = build_teacher_graph(
        call_model=call_model,
        classify_intent=classify_intent,
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
