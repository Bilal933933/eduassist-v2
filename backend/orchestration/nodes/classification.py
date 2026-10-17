"""تصنيف رسائل المستخدم بواسطة نموذج اللغة وتوجيهها."""

from collections.abc import Awaitable, Callable
from typing import cast

from orchestration.state import AgentState, Intent
from prompts.tasks import INTENT_CLASSIFICATION_TASK, INTENT_HINT
from shared.prompt_builder import build_prompt

ALLOWED_INTENTS: tuple[Intent, ...] = (
    "greeting",
    "quick_reply",
    "generation",
    "general",
    "abuse",
    "recall",
)


def create_classification_node(
    classify_intent: Callable[[str, tuple[str, ...]], Awaitable[str]],
):
    """إنشاء عقدة تصنيف تستخدم نموذجًا محقونًا بإخراج محدود."""

    async def classification_node(state: AgentState) -> dict:
        """تصنيف أحدث رسالة والتحقق من النية قبل تحديث الحالة."""
        context = state.get("context", {})
        history = context.get(
            "classifier_view", {"history": context.get("history", [])}
        )["history"]
        prompt = build_prompt(
            message=state["messages"][-1],
            context={
                "allowed_intents": list(ALLOWED_INTENTS),
                "history": history,
            },
            task=f"{INTENT_CLASSIFICATION_TASK}\n{INTENT_HINT}",
            role="intent_classifier",
        )
        result = await classify_intent(prompt, ALLOWED_INTENTS)
        intent: Intent = (
            cast(Intent, result) if result in ALLOWED_INTENTS else "generation"
        )
        return {"intent": intent}

    return classification_node


def route_intent(state: dict) -> Intent:
    """اختيار اسم العقدة التالية من التصنيف المحفوظ في الحالة."""
    # بلا تعليق AgentState عمدًا: لانغ غراف يستنتج مخطط الدخل من التعليق
    # فيقرأ من نقطة التفتيش بدل دمج المدخلات عند وجودها.
    return cast(Intent, state["intent"])
