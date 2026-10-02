"""مصنع النقل (Transport Factory) — يختار المحول حسب الإعدادات."""
from config.settings import settings
from core.ports.transport import RealtimeTransport
from realtime.adapters.sse_adapter import SSEAdapter


def create_transport(**kwargs) -> RealtimeTransport:
    """
    إنشاء محول النقل المناسب حسب الإعدادات.

    القيم المسموحة: sse | websocket | nestjs
    """
    adapter = settings.REALTIME_ADAPTER.lower()

    if adapter == "sse":
        return SSEAdapter()

    # المحولات الأخرى ستُضاف عند الحاجة الفعلية (القاعدة 10)
    raise ValueError(f"محول غير معروف: {adapter}")
