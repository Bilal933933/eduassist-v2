"""استخراج كائن JSON من رد حرّ للنموذج."""
import json
from typing import Any


def _find_object(text: str) -> str | None:
    """إيجاد أول كائن JSON متوازن في النص مع تجاهل الأقواس داخل النصوص."""
    depth = 0
    start = -1
    in_string = False
    escaped = False

    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start >= 0:
                return text[start : index + 1]
    return None


def extract_json_object(text: str) -> dict[str, Any] | None:
    """إخراج أول كائن JSON من رد النموذج أو None عند تعذّر تحليله.

    النماذج تلفّ مخرجاتها المنظّمة بأسوار الماركداون أحياناً، فيُستخرج
    الكائن من داخلها بدل رفض الرد كاملاً.
    """
    if not text:
        return None
    candidate = _find_object(text)
    if candidate is None:
        return None
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None
