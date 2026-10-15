"""الحالة المشتركة بين عقد رسم المساعد."""

import operator
from typing import Annotated, Any, Literal

from typing_extensions import TypedDict

Intent = Literal["greeting", "quick_reply", "generation"]


class AgentState(TypedDict, total=False):
    """حالة صغيرة قابلة للتوسع دون ربطها بطريقة النقل."""

    messages: Annotated[list[str], operator.add]
    intent: Intent
    response: str
    user_id: str
    context: dict[str, Any]
    task: str
    role: str
