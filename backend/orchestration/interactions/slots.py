"""سجل الحقول المطلوبة لاستكمال طلب المعلم قبل تنفيذه."""

from typing import Any

from orchestration.interactions.schema import (
    InteractionOption,
    InteractionQuestion,
)
from orchestration.state import AgentState, Intent

GRADE_OPTIONS: tuple[tuple[str, str], ...] = (
    ("الأول الإعدادي", "الأول الإعدادي"),
    ("الثاني الإعدادي", "الثاني الإعدادي"),
    ("الثالث الإعدادي", "الثالث الإعدادي"),
    ("الأول الثانوي", "الأول الثانوي"),
    ("الثاني الثانوي", "الثاني الثانوي"),
    ("الثالث الثانوي", "الثالث الثانوي"),
)

REQUIRED_SLOTS: dict[str, tuple[str, ...]] = {
    "lesson_prep": ("topic", "grade"),
    "lesson_info": ("topic",),
}

CLARIFY_INTENTS: frozenset[str] = frozenset(REQUIRED_SLOTS)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def resolve_properties(state: AgentState) -> dict[str, str]:
    """دمج خصائص النموذج مع ما هو معروف من سياق المحادثة والملف."""
    intent = state.get("intent")
    properties = state.get("properties") or {}
    context = state.get("context") or {}
    resolved: dict[str, str] = {
        key: _text(value)
        for key, value in properties.items()
        if isinstance(value, str)
    }

    if intent == "lesson_prep":
        if not resolved.get("grade"):
            resolved["grade"] = _text(context.get("grade"))
    elif intent == "lesson_info":
        if not resolved.get("topic"):
            resolved["topic"] = _text(state.get("lesson_topic"))
    elif intent == "lesson_refine":
        if not resolved.get("topic"):
            resolved["topic"] = _text(state.get("lesson_topic"))

    return {key: value for key, value in resolved.items() if value}


def missing_slots(state: AgentState) -> list[str]:
    """الحقول الحاجبة التي لا يمكن تنفيذ الطلب دونها."""
    intent = state.get("intent")
    if intent not in REQUIRED_SLOTS:
        return []
    resolved = resolve_properties(state)
    return [slot for slot in REQUIRED_SLOTS[intent] if not resolved.get(slot)]


def build_questions(state: AgentState) -> list[InteractionQuestion]:
    """تحويل الحقول الناقصة إلى أسئلة مغلقة قابلة للإجابة الحرة."""
    questions: list[InteractionQuestion] = []
    for slot in missing_slots(state):
        if slot == "grade":
            questions.append(
                InteractionQuestion(
                    slot="grade",
                    prompt="لأي صف تريد هذه الخطة؟",
                    options=[
                        InteractionOption(label=label, value=value)
                        for label, value in GRADE_OPTIONS
                    ],
                )
            )
        elif slot == "topic":
            questions.append(
                InteractionQuestion(
                    slot="topic",
                    prompt="ما عنوان الدرس الذي تريده؟",
                )
            )
    return questions[:3]


def build_question_response(
    intent: Intent,
    questions: list[InteractionQuestion],
) -> str:
    """نص قصير يظهر مع البطاقة ويشرح سبب التوقف."""
    _ = intent
    if not questions:
        return "أحتاج معلومة إضافية لإكمال طلبك."
    return "أحتاج منك المعلومات التالية لإكمال الطلب:"


def merge_answers(
    questions: list[InteractionQuestion],
    answers: dict[str, str],
) -> dict[str, str]:
    """التحقق من الإجابات وقصرها على أسئلة البطاقة."""
    allowed = {question.slot for question in questions}
    merged = {
        key: value.strip()
        for key, value in answers.items()
        if key in allowed and isinstance(value, str) and value.strip()
    }
    required = {
        question.slot
        for question in questions
        if question.required
    }
    missing = required - set(merged)
    if missing:
        raise ValueError("أكمل الحقول المطلوبة قبل الإرسال.")
    return merged


def answers_as_message(
    questions: list[InteractionQuestion],
    answers: dict[str, str],
) -> str:
    """صياغة الإجابات كرسالة مستخدم ظاهرة في سجل المحادثة."""
    labels = {question.slot: question.prompt for question in questions}
    return "، ".join(
        f"{labels.get(slot, slot)} {value}" for slot, value in answers.items()
    )
