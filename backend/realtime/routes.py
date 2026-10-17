"""مسار مقبس الويب لأحداث المحادثة."""
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.deps import get_current_ws_user, websocket_origin_is_trusted
from db.repositories import ConversationRepository
from realtime.chat_server import chat_server

router = APIRouter(prefix="/api", tags=["أحداث"])


@router.websocket("/ws/{conversation_id}")
async def events_socket(websocket: WebSocket, conversation_id: UUID) -> None:
    """إبقاء قناة أحداث المحادثة مفتوحة للمستخدم المصادق عليه فقط."""
    if not websocket_origin_is_trusted(websocket):
        await websocket.close(code=4403)
        return
    user = await get_current_ws_user(websocket)
    if user is None:
        await websocket.close(code=4401)
        return
    factory = websocket.app.state.session_factory
    async with factory() as session:
        conversation = await ConversationRepository(session).get_owned(
            conversation_id,
            user.id,
        )
    if conversation is None:
        await websocket.close(code=4404)
        return
    user_id = str(user.id)
    conversation_key = str(conversation_id)
    await chat_server.connect(user_id, conversation_key, websocket)
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
    except WebSocketDisconnect:
        pass
    finally:
        chat_server.disconnect(user_id, conversation_key, websocket)
