"""مسار HTTP لإرسال رسائل المحادثة."""
from fastapi import APIRouter, HTTPException, Request, status

from api.schemas.chat import ChatAccepted, ChatRequest
from services.chat_service import (
    EventConnectionRequiredError,
    process_chat,
)

router = APIRouter(prefix="/api", tags=["محادثة"])


@router.post("/chat", response_model=ChatAccepted)
async def chat(request: ChatRequest, http_request: Request) -> ChatAccepted:
    """تحويل طلب HTTP إلى استدعاء لخدمة المحادثة."""
    try:
        await process_chat(
            http_request.app.state.graph,
            request.teacher_id,
            request.thread_id,
            request.message,
        )
    except EventConnectionRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="يجب فتح اتصال الأحداث قبل إرسال الرسالة.",
        ) from exc

    return ChatAccepted(thread_id=request.thread_id, accepted=True)
