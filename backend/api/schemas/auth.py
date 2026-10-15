"""نماذج طلبات واستجابات المصادقة."""
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    """بيانات إنشاء حساب جديد."""

    full_name: str = Field(min_length=2, max_length=200)
    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=200)
    # التسجيل العام للمدرس والطالب فقط؛ المدير يُنشأ يدويًا خارج الواجهة.
    role: Literal["teacher", "student"] = "teacher"

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """تخفيض البريد وإزالة المسافات قبل الاستخدام."""
        return value.strip().lower()

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        """إزالة المسافات ورفض الاسم الفارغ فعليًا."""
        normalized = value.strip()
        if len(normalized) < 2:
            raise ValueError("الاسم يجب ألا يقل عن حرفين.")
        return normalized


class LoginRequest(BaseModel):
    """بيانات تسجيل الدخول."""

    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=1, max_length=200)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """تخفيض البريد وإزالة المسافات قبل الاستخدام."""
        return value.strip().lower()


class UserResponse(BaseModel):
    """بيانات المستخدم العامة (بلا تجزئة كلمة المرور)."""

    id: UUID
    full_name: str
    email: str
    role: str


class LogoutResponse(BaseModel):
    """تأكيد إنهاء جلسة المصادقة الحالية."""

    logged_out: bool
