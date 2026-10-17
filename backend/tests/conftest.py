"""أدوات مشتركة لاختبارات المشروع."""
import pytest

import api.deps as deps
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
