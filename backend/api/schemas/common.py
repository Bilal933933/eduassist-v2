"""عقد الاستجابة الموحدة (Unified Response) لنجاح وفشل HTTP."""
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """تفاصيل خطأ واحد برمز ثابت لا يعتمد على نص الرسالة."""

    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    """غلاف الفشل الموحد."""

    success: Literal[False] = False
    error: ErrorDetail


DataT = TypeVar("DataT")


class SuccessResponse(BaseModel, Generic[DataT]):
    """غلاف النجاح الموحد."""

    success: Literal[True] = True
    data: DataT


def ok(data: Any = None) -> dict:
    """بناء جسم نجاح موحد."""
    return {"success": True, "data": data}


def fail(code: str, message: str, details: Any = None) -> dict:
    """بناء جسم فشل موحد."""
    return {"success": False, "error": {"code": code, "message": message, "details": details}}
