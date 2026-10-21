"""سجل برومبتات العقد: مصدر واحد للنظام والمهمة والدور والحرارة."""

from dataclasses import dataclass

from prompts.roles import UserRole
from prompts.system.academic import LESSON_INFO_SYSTEM_PROMPT, SYSTEM_PROMPT
from prompts.system.conversational import ABUSE_SYSTEM_PROMPT, GENERAL_SYSTEM_PROMPT
from prompts.tasks.abuse import ABUSE_ESCALATION_TASK, ABUSE_RESPONSE_TASK
from prompts.tasks.classification import INTENT_CLASSIFICATION_TASK, INTENT_HINT
from prompts.tasks.general import GENERAL_RESPONSE_TASK, TEACHER_GENERAL_RESPONSE_TASK
from prompts.tasks.generation import GENERATION_TASK
from prompts.tasks.greeting import GREETING_RESPONSE_TASK, TEACHER_GREETING_RESPONSE_TASK
from prompts.tasks.lesson_info import LESSON_INFO_TASK
from prompts.tasks.summarize import RECALL_TASK

CLASSIFICATION_TASK = f"{INTENT_CLASSIFICATION_TASK}\n{INTENT_HINT}"
ABUSE_TASK = f"{ABUSE_RESPONSE_TASK}\n{ABUSE_ESCALATION_TASK}"


@dataclass(frozen=True, slots=True)
class PromptSpec:
    """مدخلات عقدة النموذج كاملة: قواعد النظام والمهمة والدور والحرارة."""

    system: str
    task: str
    role: str
    temperature: float


def _for_both(spec: PromptSpec) -> dict[UserRole, PromptSpec]:
    """المهمة نفسها للدورين حتى ينفصلا في مرحلة لاحقة."""
    return {"student": spec, "teacher": spec}


_PROMPTS: dict[str, dict[UserRole, PromptSpec]] = {
    "classification": _for_both(
        # قواعد النظام غير مستخدمة: التصنيف يعتمد الإخراج المنظم فقط.
        PromptSpec("", CLASSIFICATION_TASK, "intent_classifier", 0.0)
    ),
    "greeting": {
        "student": PromptSpec(
            SYSTEM_PROMPT, GREETING_RESPONSE_TASK, "educational_assistant", 0.3
        ),
        "teacher": PromptSpec(
            SYSTEM_PROMPT, TEACHER_GREETING_RESPONSE_TASK, "teacher_assistant", 0.3
        ),
    },
    "general": {
        "student": PromptSpec(
            GENERAL_SYSTEM_PROMPT, GENERAL_RESPONSE_TASK, "general_assistant", 0.7
        ),
        "teacher": PromptSpec(
            GENERAL_SYSTEM_PROMPT,
            TEACHER_GENERAL_RESPONSE_TASK,
            "teacher_assistant",
            0.7,
        ),
    },
    "abuse": _for_both(
        PromptSpec(ABUSE_SYSTEM_PROMPT, ABUSE_TASK, "educational_assistant", 0.2)
    ),
    "summarize": _for_both(
        PromptSpec(SYSTEM_PROMPT, RECALL_TASK, "educational_assistant", 0.2)
    ),
    "generation": {
        "student": PromptSpec(
            SYSTEM_PROMPT, GENERATION_TASK, "educational_assistant", 0.2
        ),
        "teacher": PromptSpec(SYSTEM_PROMPT, GENERATION_TASK, "teacher_assistant", 0.2),
    },
    "lesson_info": {
        "teacher": PromptSpec(
            LESSON_INFO_SYSTEM_PROMPT,
            LESSON_INFO_TASK,
            "teacher_assistant",
            0.2,
        )
    },
}


def get_prompt(node: str, role: UserRole) -> PromptSpec:
    """إرجاع برومبت العقدة للدور المطلوب ورفض أي تركيبة غير معروفة."""
    try:
        return _PROMPTS[node][role]
    except KeyError:
        raise ValueError(f"لا يوجد برومبت للعقدة {node} بالدور {role}.") from None
