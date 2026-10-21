"""قواعد النظام مقسمة حسب طبيعة الرد."""

from prompts.system.academic import LESSON_INFO_SYSTEM_PROMPT, SYSTEM_PROMPT
from prompts.system.conversational import ABUSE_SYSTEM_PROMPT, GENERAL_SYSTEM_PROMPT

__all__ = [
    "ABUSE_SYSTEM_PROMPT",
    "GENERAL_SYSTEM_PROMPT",
    "LESSON_INFO_SYSTEM_PROMPT",
    "SYSTEM_PROMPT",
]
