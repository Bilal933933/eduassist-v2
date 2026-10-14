"""أدوات مشتركة لاختبارات المشروع."""
import pytest


class FakeWebSocket:
    """اتصال تجريبي يجمع الأحداث المرسلة إليه."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    async def accept(self) -> None:
        """محاكاة قبول الاتصال."""

    async def send_json(self, event: dict) -> None:
        """حفظ الحدث المرسل للتحقق منه."""
        self.events.append(event)

    async def receive(self) -> dict:
        """محاكاة إغلاق العميل للاتصال."""
        return {"type": "websocket.disconnect"}


@pytest.fixture
def fake_websocket() -> FakeWebSocket:
    """توفير اتصال تجريبي جديد لكل اختبار."""
    return FakeWebSocket()
