"""مسار مقبس الويب لأحداث المحادثة."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from realtime.chat_server import chat_server

router = APIRouter(prefix="/api", tags=["أحداث"])


@router.websocket("/ws/{teacher_id}/{thread_id}")
async def events_socket(
    websocket: WebSocket, teacher_id: str, thread_id: str
) -> None:
    """إبقاء قناة أحداث المحادثة مفتوحة للواجهة الأمامية."""
    await chat_server.connect(teacher_id, thread_id, websocket)
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        chat_server.disconnect(teacher_id, thread_id)
