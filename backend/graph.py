"""رسم الترحيب وحالته."""
import json
import operator
from typing import Annotated, Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

GREETING_TEXT = "مرحبًا بك في مساعدك التعليمي."


class AgentState(TypedDict, total=False):
    """الحالة الدنيا اللازمة لسيناريو الترحيب."""

    messages: Annotated[list[str], operator.add]
    response: str
    teacher_id: str


def greeting_node(state: AgentState) -> dict:
    """إنتاج الترحيب دون تعديل الحالة المدخلة."""
    _ = state
    return {"response": GREETING_TEXT}


def checkpoint_config(teacher_id: str, thread_id: str) -> dict:
    """عزل حالة كل محادثة داخل نطاق المدرس."""
    scoped_thread_id = json.dumps(
        [teacher_id, thread_id], ensure_ascii=False, separators=(",", ":")
    )
    return {"configurable": {"thread_id": scoped_thread_id}}


def build_graph(checkpointer: Any | None = None):
    """تجميع رسم الترحيب مع حافظ نقاط التفتيش المحقون."""
    builder = StateGraph(AgentState)
    builder.add_node("greeting", greeting_node)
    builder.add_edge(START, "greeting")
    builder.add_edge("greeting", END)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())


# نسخة داخل الذاكرة للاختبارات والاستيراد المحلي فقط.
graph = build_graph()
