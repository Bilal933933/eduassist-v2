"""اختبارات تكامل مسارات بروفايل المعلم."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import api.routes.profile as profile_routes
from main import app
from services.errors import TeacherProfileForbiddenError
from services.profile_service import get_profile, upsert_profile


def _teacher() -> SimpleNamespace:
    """مستخدم معلم وهمي."""
    return SimpleNamespace(
        id=uuid4(), full_name="مدرس", email="teacher@example.com", role="teacher"
    )


def _student() -> SimpleNamespace:
    """مستخدم طالب وهمي."""
    return SimpleNamespace(
        id=uuid4(), full_name="طالب", email="student@example.com", role="student"
    )


def _override(user: SimpleNamespace) -> None:
    """حقن مستخدم وجلسة وهمية في اعتمادات المسار."""
    session = Mock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()

    async def fake_get_db():  # type: ignore[no-untyped-def]
        yield session

    async def fake_current_user():  # type: ignore[no-untyped-def]
        return user

    app.dependency_overrides[profile_routes.get_db] = fake_get_db
    app.dependency_overrides[profile_routes.get_current_user] = fake_current_user


def test_get_profile_returns_null_when_missing(monkeypatch) -> None:
    """إرجاع خالغ حين لا يوجد بروفايل للمعلم بعد."""

    async def fake_get_profile(*args, **kwargs):  # type: ignore[no-untyped-def]
        return None

    monkeypatch.setattr(profile_routes, "get_profile", fake_get_profile)
    _override(_teacher())
    try:
        response = TestClient(app).get("/api/profile")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"] is None
    finally:
        app.dependency_overrides.clear()


def test_put_profile_saves_and_returns_profile(monkeypatch) -> None:
    """ضبط البروفايل يحفظه ويعيده بالحقول نفسها."""

    async def fake_upsert_profile(*args, **kwargs):  # type: ignore[no-untyped-def]
        return SimpleNamespace(
            subject="النحو", class_name="الثاني المتوسط", students_note="30 طالبًا"
        )

    monkeypatch.setattr(profile_routes, "upsert_profile", fake_upsert_profile)
    _override(_teacher())
    try:
        response = TestClient(app).put(
            "/api/profile",
            json={
                "subject": "النحو",
                "class_name": "الثاني المتوسط",
                "students_note": "30 طالبًا",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["subject"] == "النحو"
        assert data["class_name"] == "الثاني المتوسط"
        assert data["students_note"] == "30 طالبًا"
    finally:
        app.dependency_overrides.clear()


def test_put_profile_rejects_student(monkeypatch) -> None:
    """الطالب لا يستطيع ضبط بروفايل معلم."""

    async def fake_upsert_profile(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise TeacherProfileForbiddenError

    monkeypatch.setattr(profile_routes, "upsert_profile", fake_upsert_profile)
    _override(_student())
    try:
        response = TestClient(app).put(
            "/api/profile",
            json={
                "subject": "النحو",
                "class_name": "الثاني المتوسط",
                "students_note": "",
            },
        )
        assert response.status_code == 403
        body = response.json()
        assert body["success"] is False
        assert body["error"]["code"] == "TEACHER_PROFILE_FORBIDDEN"
    finally:
        app.dependency_overrides.clear()


def test_service_rejects_student_role() -> None:
    """الخدمة ترفض غير المعلم قبل لمس قاعدة البيانات."""

    async def scenario() -> None:
        session = Mock()
        with pytest.raises(TeacherProfileForbiddenError):
            await get_profile(session, uuid4(), "student")
        with pytest.raises(TeacherProfileForbiddenError):
            await upsert_profile(
                session, uuid4(), "student", "النحو", "الثاني المتوسط", ""
            )

    asyncio.run(scenario())
