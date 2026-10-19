"""الحالة المشتركة بين عقد رسم المساعد."""

import operator
from typing import Annotated, Any, Literal

from typing_extensions import TypedDict

Intent = Literal[
    "greeting", "quick_reply", "generation", "general", "abuse", "recall", "lesson_prep"
]


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
    role: str
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
    role: str
    summary: str
    abuse_count: int
    sections: dict[str, str]
    metadata: dict[str, Any]
    retried_sections: list[str]
