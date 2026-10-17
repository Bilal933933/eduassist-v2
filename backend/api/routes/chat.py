"""مسار HTTP لإرسال رسائل المحادثة وإنشاء المحادثات."""
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, require_trusted_origin
from api.schemas.chat import (
    ChatAccepted,
    ChatRequest,
    ConversationCreate,
    ConversationCreated,
    ConversationItem,
    MessageItem,
    Page,
)
from api.schemas.common import SuccessResponse, ok
from db.models import User
from services.chat_service import create_conversation as create_conversation_service
from services.chat_service import process_chat
from services.conversation_service import (
    MAX_LIMIT,
    get_conversation_messages,
    list_conversations,
)

router = APIRouter(prefix="/api", tags=["محادثة"])


@router.post("/chat", response_model=SuccessResponse[ChatAccepted])
async def chat(
    payload: ChatRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
    _: None = Depends(require_trusted_origin),  # noqa: B008
) -> dict:
    """تحويل طلب HTTP إلى استدعاء لخدمة المحادثة بمالك من الجلسة."""
    await process_chat(
        http_request.app.state.graph,
        session,
        user.id,
        payload.conversation_id,
        payload.message,
        user.role,
    )
    accepted = ChatAccepted(
        conversation_id=payload.conversation_id, accepted=True
    ).model_dump(mode="json")
    return ok(accepted)


@router.post(
    "/conversations",
    response_model=SuccessResponse[ConversationCreated],
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: ConversationCreate,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
    _: None = Depends(require_trusted_origin),  # noqa: B008
) -> dict:
    """إنشاء محادثة يملكها المستخدم المصادق عليه."""
    conversation = await create_conversation_service(session, user.id, payload.title)
    created = ConversationCreated(
        id=conversation.id, title=conversation.title
    ).model_dump(mode="json")
    return ok(created)


@router.get(
    "/conversations",
    response_model=SuccessResponse[Page[ConversationItem]],
)
async def list_owned_conversations(
    session: AsyncSession = Depends(get_db),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
    limit: int = Query(default=50, ge=1, le=MAX_LIMIT),
    cursor: str | None = Query(default=None),
) -> dict:
    """جلب صفحة محادثات المستخدم من الأحدث (قراءة فقط بلا فحص مصدر)."""
    rows, next_cursor = await list_conversations(session, user.id, limit, cursor)
    page = Page[ConversationItem](
        items=[ConversationItem.model_validate(row, from_attributes=True) for row in rows],
        next_cursor=next_cursor,
    ).model_dump(mode="json")
    return ok(page)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=SuccessResponse[Page[MessageItem]],
)
async def list_owned_messages(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
    limit: int = Query(default=50, ge=1, le=MAX_LIMIT),
    cursor: str | None = Query(default=None),
) -> dict:
    """جلب صفحة رسائل محادثة مملوكة بعد المؤشر التسلسلي."""
    rows, next_cursor = await get_conversation_messages(
        session, user.id, conversation_id, limit, cursor
    )
    page = Page[MessageItem](
        items=[MessageItem.model_validate(row, from_attributes=True) for row in rows],
        next_cursor=next_cursor,
    ).model_dump(mode="json")
    return ok(page)
