"""اختبارات مصنع النقل (Transport Factory)."""
import pytest

from core.ports.transport import RealtimeTransport
from realtime.adapters.sse_adapter import SSEAdapter
from realtime.factory import create_transport


def test_create_sse_transport() -> None:
    """الاسم المحقون sse يعيد محول SSE."""
    transport = create_transport("sse")
    assert isinstance(transport, SSEAdapter)
    assert isinstance(transport, RealtimeTransport)


def test_unknown_adapter_raises() -> None:
    """الاسم المجهول يُرفض بخطأ واضح."""
    with pytest.raises(ValueError):
        create_transport("unknown")
