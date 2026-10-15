"""اختبارات ترميز مؤشرات الترقيم (Cursor Pagination)."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from services.conversation_service import (
    _decode_conversation_cursor,
    _decode_message_cursor,
    decode_cursor,
    encode_cursor,
)
from services.errors import InvalidCursorError


def test_cursor_roundtrip_preserves_payload() -> None:
    """الترميز ثم الفك يعيد نفس الحمولة."""
    payload = {"updated_at": "2026-10-15T10:00:00+00:00", "id": str(uuid4())}
    assert decode_cursor(encode_cursor(payload)) == payload


def test_cursor_is_opaque_ascii() -> None:
    """المؤشر نص لاتيني بلا كشف للحقول."""
    token = encode_cursor({"sequence_number": 7})
    token.encode("ascii")
    assert "sequence_number" not in token


def test_malformed_cursor_raises_invalid_cursor() -> None:
    """مؤشر تالف يُرفض بخطأ المؤشر المحدد."""
    with pytest.raises(InvalidCursorError):
        decode_cursor("!!!-ليس-مؤشرًا-!!!")


def test_cursor_helpers_are_pure() -> None:
    """الدوال لا تلمس الشبكة أو القاعدة."""
    now = datetime.now(timezone.utc).isoformat()
    first = encode_cursor({"updated_at": now, "id": str(uuid4())})
    second = encode_cursor({"updated_at": now, "id": str(uuid4())})
    assert decode_cursor(first)["updated_at"] == now
    assert first != second
    assert encode_cursor(decode_cursor(first)) == first


def test_conversation_cursor_rejects_naive_datetime() -> None:
    """مؤشر المحادثة يرفض التاريخ الذي لا يحمل منطقة زمنية."""
    cursor = encode_cursor(
        {"updated_at": "2026-10-15T10:00:00", "id": str(uuid4())}
    )
    with pytest.raises(InvalidCursorError):
        _decode_conversation_cursor(cursor)


def test_message_cursor_is_scoped_to_conversation() -> None:
    """مؤشر الرسائل لا يقبل استخدامه مع محادثة مختلفة."""
    source_conversation = uuid4()
    cursor = encode_cursor(
        {
            "conversation_id": str(source_conversation),
            "sequence_number": 7,
        }
    )
    assert _decode_message_cursor(cursor, source_conversation) == 7
    with pytest.raises(InvalidCursorError):
        _decode_message_cursor(cursor, uuid4())
