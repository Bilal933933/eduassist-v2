"""خدمة قراءة المحادثات والرسائل بالترقيم بالمؤشر (قراءة فقط)."""
import base64
import binascii
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories import ConversationRepository, MessageRepository
from services.errors import ConversationNotFoundError, InvalidCursorError

# ─── حدود الصفحة ───
DEFAULT_LIMIT = 50
MAX_LIMIT = 100


def normalize_limit(limit: int) -> int:
    """تقييد الحد بين 1 والأقصى دفاعًا خلف تحقق الواجهة."""
    return min(max(limit, 1), MAX_LIMIT)


def encode_cursor(payload: dict) -> str:
    """ترميز حمولة المؤشر إلى نص معتم (Opaque) لاتيني."""
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str) -> dict:
    """فك المؤشر إلى حمولته أو رفضه بخطأ المؤشر المحدد."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii"))
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, binascii.Error, UnicodeError):
        raise InvalidCursorError from None
    if not isinstance(payload, dict):
        raise InvalidCursorError from None
    return payload


def _decode_conversation_cursor(cursor: str) -> tuple[datetime, UUID]:
    """فك مؤشر المحادثات المركب (updated_at, id)."""
    payload = decode_cursor(cursor)
    try:
        updated_at = datetime.fromisoformat(payload["updated_at"])
        if updated_at.tzinfo is None or updated_at.utcoffset() is None:
            raise InvalidCursorError
        return updated_at, UUID(payload["id"])
    except (KeyError, TypeError, ValueError):
        raise InvalidCursorError from None


def _decode_message_cursor(cursor: str, conversation_id: UUID) -> int:
    """فك مؤشر الرسائل والتحقق من ارتباطه بالمحادثة المطلوبة."""
    payload = decode_cursor(cursor)
    try:
        sequence = int(payload["sequence_number"])
        cursor_conversation_id = UUID(payload["conversation_id"])
    except (KeyError, TypeError, ValueError):
        raise InvalidCursorError from None
    if sequence < 0 or cursor_conversation_id != conversation_id:
        raise InvalidCursorError from None
    return sequence


async def list_conversations(
    session: AsyncSession,
    user_id: UUID,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> tuple[list, str | None]:
    """جلب صفحة محادثات المالك من الأحدث مع مؤشر التالي."""
    page_size = normalize_limit(limit) + 1
    after = _decode_conversation_cursor(cursor) if cursor else None
    rows = await ConversationRepository(session).list_owned_page(
        user_id, page_size, after
    )
    page = rows[: normalize_limit(limit)]
    if len(rows) <= normalize_limit(limit):
        return page, None
    last = page[-1]
    return page, encode_cursor(
        {"updated_at": last.updated_at.isoformat(), "id": str(last.id)}
    )


async def get_conversation_messages(
    session: AsyncSession,
    user_id: UUID,
    conversation_id: UUID,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
) -> tuple[list, str | None]:
    """التحقق من الملكية ثم جلب صفحة رسائل بعد المؤشر التسلسلي."""
    owned = await ConversationRepository(session).get_owned(conversation_id, user_id)
    if owned is None:
        raise ConversationNotFoundError
    page_size = normalize_limit(limit) + 1
    after = _decode_message_cursor(cursor, conversation_id) if cursor else None
    rows = await MessageRepository(session).list_page_after(
        conversation_id, user_id, page_size, after
    )
    page = rows[: normalize_limit(limit)]
    if len(rows) <= normalize_limit(limit):
        return page, None
    return page, encode_cursor(
        {
            "conversation_id": str(conversation_id),
            "sequence_number": page[-1].sequence_number,
        }
    )
