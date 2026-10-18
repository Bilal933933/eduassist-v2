"""الحالة المشتركة بين عقد رسم المساعد."""

from typing import Any, Literal

from typing_extensions import TypedDict

Intent = Literal[
    "greeting", "quick_reply", "generation", "general", "abuse", "recall", "lesson_prep"
]


class AgentState(TypedDict, total=False):
    """حالة صغيرة قابلة للتوسع دون ربطها بطريقة النقل."""

    # بلا مجمع operator.add عمدًا: الموجه والجراف الفرعي يطبقان المدخلات
    # كل على حدة فيضاعف المجمع الرسائل، ولا قارئ إلا messages[-1].
    messages: list[str]
    intent: Intent
    response: str
    user_id: str
    context: dict[str, Any]
    task: str
    role: str
    summary: str
    abuse_count: int
