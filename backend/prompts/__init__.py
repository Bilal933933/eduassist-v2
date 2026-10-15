"""موجهات نماذج اللغة الكبيرة."""

from prompts.system import SYSTEM_PROMPT
from prompts.tasks import GREETING_RESPONSE_TASK, INTENT_CLASSIFICATION_TASK

__all__ = [
    "GREETING_RESPONSE_TASK",
    "INTENT_CLASSIFICATION_TASK",
    "SYSTEM_PROMPT",
]
