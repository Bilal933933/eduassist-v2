"""نماذج طلب المحادثة واستجابتها."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """بيانات رسالة المستخدم."""

    thread_id: str = Field(min_length=1)
    teacher_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ChatAccepted(BaseModel):
    """تأكيد معالجة الرسالة وإرسال أحداثها."""

    thread_id: str
    accepted: bool
