"""أدوات مشتركة لاختبارات المشروع."""
from collections.abc import AsyncIterator
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

import api.deps as deps
from db.session import open_session_factory
from services.chat_runs import active_chat_runs


class FakeWebSocket:
    """اتصال تجريبي يجمع الأحداث المرسلة إليه."""

    def __init__(self) -> None:
        self.events: list[dict] = []
        self.headers: dict[str, str] = {}
        self.cookies: dict[str, str] = {}
        self.closed_codes: list[int] = []
        self.app = None

    async def accept(self) -> None:
        """محاكاة قبول الاتصال."""

    async def send_json(self, event: dict) -> None:
        """حفظ الحدث المرسل للتحقق منه."""
        self.events.append(event)

    async def receive(self) -> dict:
        """محاكاة إغلاق العميل للاتصال."""
        return {"type": "websocket.disconnect"}

    async def close(self, code: int = 1000) -> None:
        """تسجيل رمز الإغلاق للتحقق منه."""
        self.closed_codes.append(code)


@pytest.fixture
def fake_websocket() -> FakeWebSocket:
    """توفير اتصال تجريبي جديد لكل اختبار."""
    return FakeWebSocket()


@pytest.fixture(autouse=True)
def reset_shared_state() -> None:
    """تصفير محددات المعدل وسجل التشغيلات النشطة قبل كل اختبار."""
    deps.auth_limiter.reset()
    deps.chat_limiter.reset()
    active_chat_runs.reset()


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """جلسة اختبار غير متزامنة مرتبطة بقاعدة بيانات eduassist."""
    database_url = "postgresql+psycopg://eduassist:eduassist@127.0.0.1:5432/eduassist"
    async with open_session_factory(database_url) as factory:
        async with factory() as sess:
            await sess.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            await sess.execute(text("DROP TABLE IF EXISTS knowledge_chunks CASCADE;"))
            await sess.execute(text("""
                CREATE TABLE knowledge_chunks (
                    id SERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding VECTOR(768),
                    subject VARCHAR(128),
                    grade VARCHAR(32),
                    chapter VARCHAR(128),
                    source VARCHAR(255),
                    metadata_ JSONB,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """))
            await sess.commit()
            yield sess
            await sess.rollback()
