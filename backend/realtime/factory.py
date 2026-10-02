"""مصنع النقل (Transport Factory) — يختار المحول حسب الاسم المحقون."""
from core.ports.transport import RealtimeTransport
from realtime.adapters.sse_adapter import SSEAdapter


def create_transport(adapter: str) -> RealtimeTransport:
    """
    إنشاء محول النقل المناسب حسب الاسم المحقون.

    القيم المسموحة: sse | websocket | nestjs
    """
    name = adapter.lower()

    if name == "sse":
        return SSEAdapter()

    # المحولات الأخرى ستُضاف عند الحاجة الفعلية (القاعدة 10)
    raise ValueError(f"محول غير معروف: {adapter}")
