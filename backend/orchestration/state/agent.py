"""الحالة المشتركة بين عقد رسم المساعد."""

import operator
from typing import Annotated, Any, Literal

from typing_extensions import TypedDict

Intent = Literal[
    "greeting", "quick_reply", "generation", "general", "abuse", "recall", "lesson_prep"
]


def append_node(
    metadata: dict[str, Any] | None,
    node_name: str,
    **extra: Any,
) -> dict[str, Any]:
    """دمج بيانات عقدة جديدة مع مسار العقد المنفذة دون فقد المفاتيح السابقة.

    ``nodes_path`` يبني تسلسل التنفيذ من أعلى إلى أسفل ليعرف المستخدم من أين
    جاء الرد؛ بقية المفاتيح توثّق مصدر الرد نفسه (العقدة والنية والدور).
    """
    base = dict(metadata or {})
    path = list(base.get("nodes_path") or [])
    path.append(node_name)
    return {**base, **extra, "nodes_path": path}


class AgentState(TypedDict, total=False):
    """حالة صغيرة قابلة للتوسع دون ربطها بطريقة النقل."""

    # مجمع الإضافة يحفظ تاريخ المحادثة عبر نقطة التفتيش.
    messages: Annotated[list[str], operator.add]
    intent: Intent
    response: str
    user_id: str
    user_role: Literal["teacher", "student"]
    context: dict[str, Any]
    task: str
    summary: str
    abuse_count: int
    sections: dict[str, str]
    metadata: dict[str, Any]
    retried_sections: list[str]


class AgentOutput(TypedDict, total=False):
    """حقول الرسم الفرعي التي تعود للرسم الأب دون تكرار الرسائل."""

    intent: Intent
    response: str
    task: str
    summary: str
    abuse_count: int
    sections: dict[str, str]
    metadata: dict[str, Any]
    retried_sections: list[str]


def user_is_teacher(state: AgentState) -> bool:
    """هل صاحب المحادثة معلم؟ المصدر الوحيد للدور هو ``user_role``."""
    return state.get("user_role") == "teacher"
