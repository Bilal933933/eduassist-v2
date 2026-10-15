"""مسار HTTP لإرسال رسائل المحادثة وإنشاء المحادثات."""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, require_trusted_origin
from api.schemas.chat import (
    ChatAccepted,
    ChatRequest,
    ConversationCreate,
    ConversationCreated,
)
from api.schemas.common import SuccessResponse, ok
from db.models import User
from services.chat_service import create_conversation as create_conversation_service
from services.chat_service import process_chat

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
