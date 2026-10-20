"""موجهات نماذج اللغة الكبيرة: سجل واحد يحل البرومبت بالعقدة والدور."""

from prompts.registry import PromptSpec, get_prompt
from prompts.roles import UserRole

__all__ = ["PromptSpec", "UserRole", "get_prompt"]
