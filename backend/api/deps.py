"""اعتماديات الواجهة: جلسة القاعدة والمستخدم الحالي."""
from collections.abc import AsyncIterator
from typing import Any
from fastapi import Request, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from db.models import User
from services.auth_service import get_user_by_token
from services.errors import OriginNotAllowedError, SessionInvalidError


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """فتح جلسة قاعدة بيانات واحدة لكل طلب."""
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


async def require_trusted_origin(request: Request) -> None:
    """رفض المصدر الصريح إذا لم يكن ضمن المصادر المسموحة."""
    origin = request.headers.get("origin")
    if origin is not None and origin not in settings.cors_origins_list:
        raise OriginNotAllowedError


async def get_current_user(request: Request) -> Any:
    """استخراج المستخدم من كوكي الجلسة أو رفض الطلب قبل لمس القاعدة."""
    raw_token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not raw_token:
        raise SessionInvalidError
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise SessionInvalidError
    async with factory() as session:
        user = await get_user_by_token(session, raw_token)
    if user is None:
        raise SessionInvalidError
    return user


async def get_current_ws_user(websocket: WebSocket) -> User | None:
    """استخراج المستخدم من كوكي مقبس الويب، أو لا شيء عند غيابه."""
    raw_token = websocket.cookies.get(settings.AUTH_COOKIE_NAME)
    if not raw_token:
        return None
    factory = getattr(websocket.app.state, "session_factory", None)
    if factory is None:
        return None
    async with factory() as session:
        return await get_user_by_token(session, raw_token)


def websocket_origin_is_trusted(websocket: WebSocket) -> bool:
    """التحقق من مصدر مصافحة مقبس الويب عند وجوده."""
    origin = websocket.headers.get("origin")
    return origin is None or origin in settings.cors_origins_list
