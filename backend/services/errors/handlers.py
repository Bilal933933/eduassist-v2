"""المعالجة المركزية للأخطاء (Error Handling) وتحويلها للعقد الموحد."""
import logging
from typing import Any

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.schemas.common import fail
from services.errors import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

logger = logging.getLogger("eduassist.errors")

# ─── الحالة من فئة الخطأ العامة لا من الحالة المحددة ───
ERROR_STATUS_BY_CATEGORY: tuple[tuple[type[AppError], int], ...] = (
    (AuthenticationError, status.HTTP_401_UNAUTHORIZED),
    (AuthorizationError, status.HTTP_403_FORBIDDEN),
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConflictError, status.HTTP_409_CONFLICT),
    (RateLimitError, status.HTTP_429_TOO_MANY_REQUESTS),
    (ValidationError, status.HTTP_422_UNPROCESSABLE_CONTENT),
)


def status_for_error(exc: AppError) -> int:
    """اختيار حالة HTTP من فئة الخطأ العامة لا من الحالة المحددة."""
    for category, status_code in ERROR_STATUS_BY_CATEGORY:
        if isinstance(exc, category):
            return status_code
    return status.HTTP_400_BAD_REQUEST


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """تحويل خطأ تطبيق معروف إلى استجابة HTTP موحدة."""
    _ = request
    status_code = status_for_error(exc)
    headers = (
        {"Retry-After": str(exc.retry_after)}
        if isinstance(exc, RateLimitError)
        else None
    )
    return JSONResponse(
        status_code=status_code,
        content=fail(exc.code, exc.message),
        headers=headers,
    )


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """تحويل أخطاء التحقق إلى تفاصيل حقول قابلة للتسلسل."""
    _ = request
    details = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=fail(
            "VALIDATION_ERROR",
            "بيانات الطلب غير صالحة.",
            jsonable_encoder(details),
        ),
    )


async def handle_http_error(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """تغليف أخطاء HTTP العامة بالعقد الموحد."""
    _ = request
    code = f"HTTP_{exc.status_code}"
    message = str(exc.detail) if exc.detail else "خطأ في الطلب."
    return JSONResponse(status_code=exc.status_code, content=fail(code, message))


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """تسجيل الخطأ الداخلي وإرجاع رسالة عامة دون تسريب التفاصيل."""
    logger.exception(
        "خطأ غير متوقع في %s %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=fail("INTERNAL_ERROR", "حدث خطأ غير متوقع. حاول لاحقًا."),
    )


def register_error_handlers(app: Any) -> None:
    """تسجيل معالجات الأخطاء المركزية مرة واحدة."""
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
