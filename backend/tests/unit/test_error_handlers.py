"""اختبارات المعالجة المركزية للأخطاء والعقد الموحد."""
import asyncio
import json
from unittest.mock import Mock

from services.errors import (
    ALL_ERRORS,
    AccountInactiveError,
    AppError,
    ChatBusyError,
    EmailAlreadyExistsError,
    EventConnectionRequiredError,
    InvalidCredentialsError,
    InvalidRoleError,
    NotFoundError,
    OriginNotAllowedError,
    RateLimitExceededError,
    SessionInvalidError,
)
from services.errors.handlers import (
    handle_app_error,
    handle_unexpected_error,
    handle_validation_error,
    status_for_error,
)


def _request() -> Mock:
    """طلب وهمي بأقل الحقول التي يستخدمها المعالج."""
    request = Mock()
    request.method = "POST"
    request.url.path = "/api/auth/login"
    return request


def _body(response) -> dict:  # type: ignore[no-untyped-def]
    """استخراج جسم JSON من استجابة المعالج."""
    return json.loads(response.body.decode("utf-8"))


def test_each_app_error_has_unified_shape() -> None:
    """كل خطأ معروف يرجع الحالة والرمز والشكل الموحد."""
    cases = [
        (EmailAlreadyExistsError(), 409, "EMAIL_TAKEN"),
        (InvalidCredentialsError(), 401, "INVALID_CREDENTIALS"),
        (AccountInactiveError(), 403, "ACCOUNT_INACTIVE"),
        (InvalidRoleError(), 422, "ROLE_NOT_ALLOWED"),
        (SessionInvalidError(), 401, "SESSION_INVALID"),
        (OriginNotAllowedError(), 403, "ORIGIN_NOT_ALLOWED"),
        (NotFoundError("conversation"), 404, "CONVERSATION_NOT_FOUND"),
        (NotFoundError("message"), 404, "MESSAGE_NOT_FOUND"),
        (NotFoundError("unknown-thing", "رسالة مخصصة."), 404, "UNKNOWN-THING_NOT_FOUND"),
        (EventConnectionRequiredError(), 409, "EVENT_CONNECTION_REQUIRED"),
        (ChatBusyError(), 409, "CHAT_BUSY"),
        (RateLimitExceededError(), 429, "RATE_LIMITED"),
    ]
    for exc, expected_status, expected_code in cases:
        response = asyncio.run(handle_app_error(_request(), exc))
        assert response.status_code == expected_status
        body = _body(response)
        assert body["success"] is False
        assert body["error"]["code"] == expected_code
        assert body["error"]["details"] is None


def test_every_error_carries_code_status_and_message() -> None:
    """كل خطأ في الحزمة يحمل رمزًا وحالة ورسالة صالحة."""
    codes = set()
    for error_class in ALL_ERRORS:
        assert issubclass(error_class, AppError)
        assert 400 <= status_for_error(error_class()) <= 599
        assert error_class.code and error_class.code == error_class.code.upper()
        assert error_class.message
        codes.add(error_class.code)
    assert len(codes) == len(ALL_ERRORS)


def test_unexpected_error_returns_generic_500() -> None:
    """الخطأ غير المتوقع يرجع 500 عامًا بلا تفاصيل داخلية."""
    response = asyncio.run(
        handle_unexpected_error(_request(), RuntimeError("postgres://secret"))
    )
    assert response.status_code == 500
    body = _body(response)
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert "postgres" not in json.dumps(body)


def test_validation_error_lists_fields() -> None:
    """خطأ التحقق يرجع 422 مع قائمة الحقول."""
    from fastapi.exceptions import RequestValidationError

    exc = RequestValidationError(
        [
            {
                "loc": ("body", "password"),
                "msg": "Field required",
                "type": "missing",
            }
        ]
    )
    response = asyncio.run(handle_validation_error(_request(), exc))
    assert response.status_code == 422
    body = _body(response)
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"] == [
        {"field": "body.password", "message": "Field required"}
    ]


def test_rate_limit_error_sends_retry_after_header() -> None:
    """خطأ تجاوز المعدل يرجع 429 مع ترويسة Retry-After."""
    response = asyncio.run(handle_app_error(_request(), RateLimitExceededError(42)))
    assert response.status_code == 429
    assert response.headers["retry-after"] == "42"


def test_rate_limit_retry_after_has_floor_of_one_second() -> None:
    """زمن الانتظار لا ينزل عن ثانية واحدة."""
    assert RateLimitExceededError(0).retry_after == 1
