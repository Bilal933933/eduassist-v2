"""بناء مدخل موحد يرسل إلى نموذج اللغة الكبير."""

import json
from typing import Any


def build_prompt(
    message: str,
    context: dict[str, Any],
    task: str,
    role: str,
) -> str:
    """جمع الرسالة والسياق والمهمة والدور داخل جيسون (JSON)."""
    if not message.strip():
        raise ValueError("لا يمكن بناء الموجه دون رسالة.")
    return json.dumps(
        {
            "message": message,
            "context": context,
            "task": task,
            "role": role,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
