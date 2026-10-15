"""اختبارات تكامل مسارات المصادقة بعزل قاعدة البيانات."""
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

import api.routes.auth as auth_routes
from main import app


def _fake_user() -> Mock:
    """مستخدم وهمي للاستجابات."""
    user = Mock()
    user.id = uuid4()
    user.full_name = "مدرس تجريبي"
    user.email = "teacher@example.com"
    user.role = "teacher"
    return user


def _override_db(monkeypatch, session: Mock) -> None:
    """حقن جلسة وهمية في اعتمادية قاعدة البيانات."""

    async def fake_get_db():  # type: ignore[no-untyped-def]
        yield session

    app.dependency_overrides[auth_routes.get_db] = fake_get_db
    monkeypatch.setattr(
        auth_routes, "get_db", fake_get_db, raising=False
    )


def test_register_sets_session_cookie(monkeypatch) -> None:
    """التسجيل يعيد 201 ويضبط كوكي الجلسة كـ HttpOnly."""
    from db.models import AuthSession, User

    user = _fake_user()
    session = Mock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()

    async def fake_scalar(statement):  # type: ignore[no-untyped-def]
        entity = statement.column_descriptions[0]["entity"]
        if entity is User:
            # أول استدعاء: فحص التكرار (لا يوجد)، ثم إنشاء المستخدم
            if not hasattr(fake_scalar, "called"):
                fake_scalar.called = True  # type: ignore[attr-defined]
                return None
            return user
        return None

    session.scalar = AsyncMock(side_effect=fake_scalar)
    _override_db(monkeypatch, session)

    async def fake_register(*args, **kwargs):  # type: ignore[no-untyped-def]
        return user, "raw-test-token-123"

    monkeypatch.setattr(auth_routes, "register_user", fake_register)
    try:
        response = TestClient(app).post(
            "/api/auth/register",
            json={
                "full_name": "مدرس تجريبي",
                "email": "teacher@example.com",
                "password": "كلمة-قوية-123",
                "role": "teacher",
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["email"] == "teacher@example.com"
        cookie = response.headers.get("set-cookie", "")
        assert "eduassist_session=" in cookie
        assert "HttpOnly" in cookie
    finally:
        app.dependency_overrides.clear()


def test_me_requires_login() -> None:
    """مسار المستخدم الحالي يرفض 401 بلا كوكي."""
    app.dependency_overrides.clear()
    response = TestClient(app).get("/api/auth/me")
    assert response.status_code == 401


def test_login_rejects_invalid_credentials(monkeypatch) -> None:
    """الدخول ببيانات خاطئة يعيد 401."""
    from services.auth_service import InvalidCredentialsError

    session = Mock()
    session.commit = AsyncMock()
    _override_db(monkeypatch, session)

    async def fake_login(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise InvalidCredentialsError

    monkeypatch.setattr(auth_routes, "login_user", fake_login)
    try:
        response = TestClient(app).post(
            "/api/auth/login",
            json={"email": "t@example.com", "password": "خاطئة"},
        )
        assert response.status_code == 401
        assert response.json() == {
            "success": False,
            "error": {
                "code": "INVALID_CREDENTIALS",
                "message": "البريد أو كلمة المرور غير صحيحة.",
                "details": None,
            },
        }
    finally:
        app.dependency_overrides.clear()


def test_me_returns_unified_success() -> None:
    """مسار المستخدم الحالي يرجع الغلاف الموحد."""
    user = _fake_user()
    app.dependency_overrides[auth_routes.get_current_user] = lambda: user
    try:
        response = TestClient(app).get("/api/auth/me")
        assert response.status_code == 200
        assert response.json() == {
            "success": True,
            "data": {
                "id": str(user.id),
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role,
            },
        }
    finally:
        app.dependency_overrides.clear()


def test_register_duplicate_returns_unified_error(monkeypatch) -> None:
    """تعارض البريد يرجع 409 بالعقد الموحد."""
    from services.errors import EmailAlreadyExistsError

    session = Mock()
    session.commit = AsyncMock()
    _override_db(monkeypatch, session)

    async def fake_register(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise EmailAlreadyExistsError

    monkeypatch.setattr(auth_routes, "register_user", fake_register)
    try:
        response = TestClient(app).post(
            "/api/auth/register",
            json={
                "full_name": "مدرس تجريبي",
                "email": "teacher@example.com",
                "password": "كلمة-قوية-123",
                "role": "teacher",
            },
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "EMAIL_TAKEN"
        assert response.json()["success"] is False
    finally:
        app.dependency_overrides.clear()


def test_validation_error_returns_unified_shape(monkeypatch) -> None:
    """بيانات ناقصة ترجع 422 بالعقد الموحد."""
    session = Mock()
    session.commit = AsyncMock()
    _override_db(monkeypatch, session)
    try:
        response = TestClient(app).post("/api/auth/login", json={"email": "t@e.com"})
        assert response.status_code == 422
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.clear()


def test_unexpected_error_hides_details(monkeypatch) -> None:
    """الخطأ غير المتوقع يرجع 500 عامًا بلا تسريب."""
    session = Mock()
    session.commit = AsyncMock()
    _override_db(monkeypatch, session)

    async def fake_login(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise RuntimeError("تفاصيل قاعدة بيانات حساسة: postgres://...")

    monkeypatch.setattr(auth_routes, "login_user", fake_login)
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/auth/login",
            json={"email": "t@example.com", "password": "كلمة-قوية-123"},
        )
        assert response.status_code == 500
        body = response.json()
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert "postgres" not in response.text
    finally:
        app.dependency_overrides.clear()


def test_logout_returns_unified_success(monkeypatch) -> None:
    """الخروج يرجع نجاحًا موحدًا ويمسح الكوكي."""
    user = _fake_user()
    session = Mock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    _override_db(monkeypatch, session)
    app.dependency_overrides[auth_routes.get_current_user] = lambda: user

    async def fake_logout(*args, **kwargs):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr(auth_routes, "logout_user", fake_logout)
    try:
        client = TestClient(app)
        client.cookies.set("eduassist_session", "raw-token")
        response = client.post("/api/auth/logout")
        assert response.status_code == 200
        assert response.json() == {"success": True, "data": {"logged_out": True}}
    finally:
        app.dependency_overrides.clear()
