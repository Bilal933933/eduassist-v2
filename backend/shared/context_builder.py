"""بناء سياق المحادثة بشكل موحد لتمريره إلى الرسم."""

from typing import Any, Protocol

CONTEXT_HISTORY_LIMIT = 10
CLASSIFIER_WINDOW = 4
GENERATOR_WINDOW = 10
CLASSIFIER_MAX_CHARS = 120
GENERATOR_MAX_CHARS = 300
TOPICS_LIMIT = 3


class _HistoryRow(Protocol):
    """أقل ما نحتاجه من صف الرسالة لبناء السياق."""

    sender: str
    content: str


def _clean(rows: list[_HistoryRow], max_chars: int) -> list[dict[str, str]]:
    """إسقاط الفارغ وتوحيد المرسل وقص الطويل."""
    cleaned: list[dict[str, str]] = []
    for row in rows:
        content = (row.content or "").strip()
        if not content:
            continue
        sender = row.sender if row.sender in ("user", "assistant") else "user"
        cleaned.append({"sender": sender, "content": content[:max_chars]})
    return cleaned


def build_history_context(
    rows: list[_HistoryRow],
    limit: int = CONTEXT_HISTORY_LIMIT,
) -> dict[str, Any]:
    """تحويل صفوف الرسائل إلى سياق history مرتب ومحدود."""
    tail = rows[-limit:] if limit > 0 else []
    return {
        "history": [
            {"sender": row.sender, "content": row.content} for row in tail
        ]
    }


def build_classifier_view(
    rows: list[_HistoryRow],
    limit: int = CLASSIFIER_WINDOW,
) -> dict[str, Any]:
    """ذيل قصير نظيف للمصنف لحل الضمائر بلا ضجيج."""
    tail = rows[-limit:] if limit > 0 else []
    return {"history": _clean(tail, CLASSIFIER_MAX_CHARS)}


def build_generator_view(
    rows: list[_HistoryRow],
    limit: int = GENERATOR_WINDOW,
) -> dict[str, Any]:
    """نافذة كاملة للمولد مع آخر مواضيع المستخدم للتلخيص."""
    tail = rows[-limit:] if limit > 0 else []
    history = _clean(tail, GENERATOR_MAX_CHARS)
    topics = [
        item["content"][:60] for item in history if item["sender"] == "user"
    ][-TOPICS_LIMIT:]
    return {"history": history, "last_topics": topics}
