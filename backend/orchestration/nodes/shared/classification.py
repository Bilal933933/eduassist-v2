"""تصنيف رسائل المستخدم بواسطة نموذج اللغة وتوجيهها."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any, cast

from orchestration.interactions.schema import Interpretation
from orchestration.state import AgentState, Intent, append_node, current_user_role
from prompts import get_prompt
from shared.json_parser import extract_json_object
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
    "lesson_refine",
    "lesson_info",
)

STUDENT_INTENTS: tuple[Intent, ...] = (
    "greeting",
    "quick_reply",
    "generation",
    "general",
    "abuse",
    "recall",
)


def _parse_interpretation(
    raw: dict[str, Any] | str,
    message: str,
    allowed_intents: tuple[Intent, ...],
):
    """التحقق من إخراج المصنف المنظم ومطابقته للرسالة الأصلية."""
    data = raw if isinstance(raw, dict) else extract_json_object(raw)
    if not data:
        return None
    try:
        interpretation = Interpretation.model_validate(data)
    except ValueError:
        return None
    payload = interpretation.message
    if payload.text.strip() != message.strip():
        return None
    if payload.intent not in allowed_intents:
        return None
    return payload


def create_classification_node(
    classify_intent: Callable[[str, tuple[str, ...]], Awaitable[str]],
    allowed_intents: tuple[Intent, ...],
    interpret_intent: (
        Callable[[str, tuple[str, ...]], Awaitable[dict[str, Any] | str]] | None
    ) = None,
):
    """إنشاء عقدة تصنيف تستخدم نموذجًا محقونًا بإخراج محدود."""

    async def classification_node(state: AgentState) -> dict:
        """تصنيف أحدث رسالة والتحقق من النية قبل تحديث الحالة."""
        context = state.get("context", {})
        message = state["messages"][-1]
        resume = context.get("interaction_resume")
        if isinstance(resume, dict):
            resumed_intent = resume.get("intent")
            if resumed_intent in allowed_intents:
                properties = resume.get("properties")
                return {
                    "intent": cast(Intent, resumed_intent),
                    "properties": (
                        dict(properties) if isinstance(properties, dict) else {}
                    ),
                    "properties_ready": True,
                    "metadata": append_node(
                        state.get("metadata"),
                        "classify",
                        intent=resumed_intent,
                        classified_by="interaction_resume",
                        classifier_task="stored_interaction",
                        classifier_failed=False,
                    ),
                }

        history = context.get(
            "classifier_view", {"history": context.get("history", [])}
        )["history"]
        spec = get_prompt("classification", current_user_role(state))
        prompt = build_prompt(
            message=message,
            context={
                "allowed_intents": list(allowed_intents),
                "history": history,
                # وجود الخطة يغيّر معنى "عدّله/وسّعه" إلى تعديل خطة سابقة.
                "lesson_plan_available": bool(state.get("lesson_plan")),
                "lesson_topic": state.get("lesson_topic", ""),
            },
            task=spec.task,
            role=spec.role,
        )
        classifier_failed = False
        structured_failed = False
        properties: dict[str, Any] = {}
        properties_ready = False
        intent: Intent | None = None

        if interpret_intent is not None:
            try:
                raw = await interpret_intent(prompt, allowed_intents)
                interpreted = _parse_interpretation(
                    raw, message, allowed_intents
                )
                if interpreted is None:
                    raise ValueError("إخراج المصنف المنظم لا يطابق العقد.")
            except Exception:
                logger.exception(
                    "فشل التفسير المنظم، ستُستخدم نتيجة المصنف القديم."
                )
                structured_failed = True
            else:
                intent = interpreted.intent
                properties = interpreted.properties.model_dump(exclude_none=True)
                properties_ready = True

        if intent is None:
            try:
                result = await classify_intent(prompt, allowed_intents)
            except Exception:
                # فشل التصنيف لا يجوز أن يمنع الرد: التوليد هو المسار الآمن.
                logger.exception(
                    "فشل تصنيف النية، تحويل الرسالة إلى مسار التوليد."
                )
                result = "generation"
                classifier_failed = True
            intent = (
                cast(Intent, result)
                if result in allowed_intents
                else "generation"
            )

        return {
            "intent": intent,
            "properties": properties,
            "properties_ready": properties_ready,
            "metadata": append_node(
                state.get("metadata"),
                "classify",
                intent=intent,
                classified_by="classification_node",
                classifier_task="intent_classifier",
                classifier_failed=classifier_failed,
                structured_interpretation=properties_ready,
                structured_fallback=structured_failed,
            ),
        }

    return classification_node


def route_intent(state: AgentState) -> Intent:
    """اختيار اسم العقدة التالية من التصنيف المحفوظ في الحالة."""
    return cast(Intent, state["intent"])
