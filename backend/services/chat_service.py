"""خدمة تشغيل رسم المحادثة وإصدار أحداثه."""
from typing import Any

from graph import checkpoint_config
from realtime.chat_server import chat_server


class EventConnectionRequiredError(Exception):
    """خطأ يدل على غياب اتصال الأحداث المطلوب."""


async def process_chat(
    graph: Any, teacher_id: str, thread_id: str, message: str
) -> None:
    """تشغيل الرسم وإرسال أحداث البداية والاكتمال."""
    if not chat_server.is_connected(teacher_id, thread_id):
        raise EventConnectionRequiredError

    await chat_server.send_started(teacher_id, thread_id)
    event_stream = graph.astream_events(
        {"messages": [message], "teacher_id": teacher_id},
        checkpoint_config(teacher_id, thread_id),
        version="v2",
    )
    async for event in event_stream:
        if event.get("event") == "on_chain_end" and event.get("name") == "greeting":
            output = event.get("data", {}).get("output", {})
            await chat_server.send_completed(
                teacher_id,
                thread_id,
                output["response"],
            )
