"""نماذج طلب المحادثة واستجابتها."""
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """بيانات رسالة المستخدم (المالك من الجلسة، لا من العميل)."""

    conversation_id: UUID
    message: str = Field(min_length=1)


class ChatAccepted(BaseModel):
    """تأكيد معالجة الرسالة وإرسال أحداثها."""

    conversation_id: UUID
    accepted: bool


class ConversationCreate(BaseModel):
    """بيانات إنشاء محادثة جديدة."""

    title: str | None = Field(default=None, max_length=200)


class ConversationCreated(BaseModel):
    """بيانات المحادثة المنشأة."""

    id: UUID
    title: str | None
