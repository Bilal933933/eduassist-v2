"""نماذج طلب المحادثة واستجابتها."""
from datetime import datetime
from typing import Any, Generic, Literal, TypeVar
from uuid import UUID

from pydantic import AliasChoices, BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    """بيانات رسالة المستخدم أو إجابة بطاقة استكمال البيانات."""

    conversation_id: UUID
    message: str = ""
    interaction_id: UUID | None = None
    answers: dict[str, str] | None = None
    action: Literal["send", "answer", "dismiss"] = "send"

    @model_validator(mode="after")
    def validate_action(self) -> "ChatRequest":
        if self.action == "dismiss":
            if self.interaction_id is None:
                raise ValueError("معرّف البطاقة مطلوب للإهمال.")
            if self.answers is not None:
                raise ValueError("لا تُرسل إجابات مع الإهمال.")
            return self
        if self.interaction_id is not None:
            if self.action != "answer":
                raise ValueError("الإجراء يجب أن يكون answer مع البطاقة.")
            if not self.answers:
                raise ValueError("أرسل إجابة واحدة على الأقل.")
            if len(self.answers) > 3:
                raise ValueError("عدد الإجابات يتجاوز حد الأسئلة.")
            return self
        if self.action != "send":
            raise ValueError("الإجراء غير صالح دون بطاقة.")
        if not self.message.strip():
            raise ValueError("نص الرسالة مطلوب.")
        return self


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
    # ميتا ديتا مصدر الرد: تُقرأ من السمة metadata_ لأن "metadata" محجوزة في SQLAlchemy.
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata_", "metadata"),
    )
    interaction: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("interaction_", "interaction"),
    )


ItemT = TypeVar("ItemT")


class Page(BaseModel, Generic[ItemT]):
    """صفحة واحدة: العناصر ومؤشر التالي (null عند النهاية)."""

    items: list[ItemT]
    next_cursor: str | None = None
