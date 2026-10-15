"""تصنيف رسائل المستخدم بواسطة نموذج اللغة وتوجيهها."""

from collections.abc import Awaitable, Callable
from typing import cast

from orchestration.state import AgentState, Intent
from shared.prompt_builder import build_prompt

ALLOWED_INTENTS: tuple[Intent, ...] = ("greeting", "quick_reply", "generation")


def create_classification_node(
    classify_intent: Callable[[str, tuple[str, ...]], Awaitable[str]],
):
    """إنشاء عقدة تصنيف تستخدم نموذجًا محقونًا بإخراج محدود."""

    async def classification_node(state: AgentState) -> dict:
        """تصنيف أحدث رسالة والتحقق من النية قبل تحديث الحالة."""
        prompt = build_prompt(
            message=state["messages"][-1],
            context={"allowed_intents": list(ALLOWED_INTENTS)},
            task="classify_intent",
            role="intent_classifier",
        )
        result = await classify_intent(prompt, ALLOWED_INTENTS)
        intent: Intent = (
            cast(Intent, result) if result in ALLOWED_INTENTS else "generation"
        )
        return {"intent": intent}

    return classification_node


def route_intent(state: AgentState) -> Intent:
    """اختيار اسم العقدة التالية من التصنيف المحفوظ في الحالة."""
    return cast(Intent, state["intent"])
