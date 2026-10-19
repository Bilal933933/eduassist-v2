"""تصنيف رسائل المستخدم بواسطة نموذج اللغة وتوجيهها."""

from collections.abc import Awaitable, Callable
from typing import cast

from orchestration.state import AgentState, Intent
from prompts.tasks import INTENT_CLASSIFICATION_TASK, INTENT_HINT
from shared.prompt_builder import build_prompt

TEACHER_INTENTS: tuple[Intent, ...] = (
    "greeting",
    "quick_reply",
    "generation",
    "general",
    "abuse",
    "recall",
    "lesson_prep",
)

STUDENT_INTENTS: tuple[Intent, ...] = (
    "greeting",
    "quick_reply",
    "generation",
    "general",
    "abuse",
    "recall",
)


def create_classification_node(
    classify_intent: Callable[[str, tuple[str, ...]], Awaitable[str]],
    allowed_intents: tuple[Intent, ...],
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
                "allowed_intents": list(allowed_intents),
                "history": history,
            },
            task=f"{INTENT_CLASSIFICATION_TASK}\n{INTENT_HINT}",
            role="intent_classifier",
        )
        result = await classify_intent(prompt, allowed_intents)
        intent: Intent = (
            cast(Intent, result) if result in allowed_intents else "generation"
        )
        return {
            "intent": intent,
            "metadata": {
                **state.get("metadata", {}),
                "classified_as": intent,
                "classifier_node": "classification_node",
                "classifier_task": "intent_classifier",
            },
        }

    return classification_node


def route_intent(state: AgentState) -> Intent:
    """اختيار اسم العقدة التالية من التصنيف المحفوظ في الحالة."""
    return cast(Intent, state["intent"])
