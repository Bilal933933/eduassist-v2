"""تصنيف رسائل المستخدم بواسطة نموذج اللغة وتوجيهها."""

import logging
from collections.abc import Awaitable, Callable
from typing import cast

from orchestration.state import AgentState, Intent, append_node, current_user_role
from prompts import get_prompt
from shared.prompt_builder import build_prompt

logger = logging.getLogger("eduassist.classification")

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
        spec = get_prompt("classification", current_user_role(state))
        prompt = build_prompt(
            message=state["messages"][-1],
            context={
                "allowed_intents": list(allowed_intents),
                "history": history,
            },
            task=spec.task,
            role=spec.role,
        )
        classifier_failed = False
        try:
            result = await classify_intent(prompt, allowed_intents)
        except Exception:
            # فشل التصنيف لا يجوز أن يمنع الرد: التوليد هو المسار الآمن.
            logger.exception("فشل تصنيف النية، تحويل الرسالة إلى مسار التوليد.")
            result = "generation"
            classifier_failed = True
        intent: Intent = (
            cast(Intent, result) if result in allowed_intents else "generation"
        )
        return {
            "intent": intent,
            "metadata": append_node(
                state.get("metadata"),
                "classify",
                intent=intent,
                classified_by="classification_node",
                classifier_task="intent_classifier",
                classifier_failed=classifier_failed,
            ),
        }

    return classification_node


def route_intent(state: AgentState) -> Intent:
    """اختيار اسم العقدة التالية من التصنيف المحفوظ في الحالة."""
    return cast(Intent, state["intent"])
