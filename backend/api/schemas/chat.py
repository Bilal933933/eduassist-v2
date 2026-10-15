"""نماذج طلب المحادثة واستجابتها."""
from datetime import datetime
from typing import Generic, TypeVar
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


class ConversationItem(BaseModel):
    """كل بيانات محادثة واحدة في القائمة."""

    id: UUID
    title: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class MessageItem(BaseModel):
    """كل بيانات رسالة واحدة."""

    id: UUID
    sender: str
    content: str
    sequence_number: int
    created_at: datetime


ItemT = TypeVar("ItemT")


class Page(BaseModel, Generic[ItemT]):
    """صفحة واحدة: العناصر ومؤشر التالي (null عند النهاية)."""

    items: list[ItemT]
    next_cursor: str | None = None
