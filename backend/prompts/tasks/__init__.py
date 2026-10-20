"""مهام العقد، لكل عقدة وحدة، وتُختار بالدور عبر سجل البرومبتات."""

from prompts.tasks.abuse import ABUSE_ESCALATION_TASK, ABUSE_RESPONSE_TASK
from prompts.tasks.classification import INTENT_CLASSIFICATION_TASK, INTENT_HINT
from prompts.tasks.general import GENERAL_RESPONSE_TASK, TEACHER_GENERAL_RESPONSE_TASK
from prompts.tasks.generation import GENERATION_TASK
from prompts.tasks.greeting import GREETING_RESPONSE_TASK, TEACHER_GREETING_RESPONSE_TASK
from prompts.tasks.summarize import RECALL_TASK

__all__ = [
    "ABUSE_ESCALATION_TASK",
    "ABUSE_RESPONSE_TASK",
    "GENERAL_RESPONSE_TASK",
    "GENERATION_TASK",
    "GREETING_RESPONSE_TASK",
    "INTENT_CLASSIFICATION_TASK",
    "INTENT_HINT",
    "RECALL_TASK",
    "TEACHER_GENERAL_RESPONSE_TASK",
    "TEACHER_GREETING_RESPONSE_TASK",
]
