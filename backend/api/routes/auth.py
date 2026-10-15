"""مسارات المصادقة: التسجيل والدخول والخروج والمستخدم الحالي."""
from typing import Any

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, require_trusted_origin
from api.schemas.auth import LoginRequest, LogoutResponse, RegisterRequest, UserResponse
from api.schemas.common import SuccessResponse, ok
from config.settings import settings
from services.auth_service import login_user, logout_user, register_user

router = APIRouter(prefix="/api/auth", tags=["مصادقة"])


def _set_session_cookie(response: Response, raw_token: str) -> None:
    """ضبط كوكي الجلسة كـ HttpOnly مع Lax."""
    is_production = settings.ENV == "production"
    response.set_cookie(
        key=settings.AUTH_COOKIE_NAME,
        value=raw_token,
        max_age=settings.AUTH_SESSION_DAYS * 24 * 3600,
        httponly=True,
        secure=is_production,
        samesite="lax",
        path="/",
    )


def _to_user_payload(user: Any) -> dict:
    """تحويل صف المستخدم إلى حمولة عامة (بلا تجزئة كلمة المرور)."""
    validated = UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
    )
    return validated.model_dump(mode="json")


@router.post(
    "/register",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    _: None = Depends(require_trusted_origin),  # noqa: B008
) -> dict:
    """إنشاء حساب جديد وبدء جلسة له (الأخطاء للمعالج المركزي)."""
    user, raw_token = await register_user(
        session,
        payload.full_name.strip(),
        payload.email,
        payload.password,
        payload.role,
        settings.AUTH_SESSION_DAYS,
    )
    await session.commit()
    _set_session_cookie(response, raw_token)
    return ok(_to_user_payload(user))


@router.post("/login", response_model=SuccessResponse[UserResponse])
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    _: None = Depends(require_trusted_origin),  # noqa: B008
) -> dict:
    """تسجيل الدخول وبدء جلسة جديدة (الأخطاء للمعالج المركزي)."""
    user, raw_token = await login_user(
        session,
        payload.email,
        payload.password,
        settings.AUTH_SESSION_DAYS,
    )
    await session.commit()
    _set_session_cookie(response, raw_token)
    return ok(_to_user_payload(user))


@router.post("/logout", response_model=SuccessResponse[LogoutResponse])
async def logout(
    response: Response,
    http_request: Request,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    user: Any = Depends(get_current_user),  # noqa: B008
    _: None = Depends(require_trusted_origin),  # noqa: B008
) -> dict:
    """إنهاء الجلسة الحالية من القاعدة ومسح الكوكي برد موحد."""
    _ = user
    raw_token = http_request.cookies.get(settings.AUTH_COOKIE_NAME)
    if raw_token:
        await logout_user(session, raw_token)
        await session.commit()
    response.delete_cookie(key=settings.AUTH_COOKIE_NAME, path="/")
    return ok({"logged_out": True})


@router.get("/me", response_model=SuccessResponse[UserResponse])
async def me(user: Any = Depends(get_current_user)) -> dict:  # noqa: B008
    """إرجاع بيانات المستخدم الحالي المصادق عليه."""
    return ok(_to_user_payload(user))
