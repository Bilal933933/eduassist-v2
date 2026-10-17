"""اختبارات عقدة الرد العام المحقونة."""

import asyncio
import json

from orchestration.nodes.shared.general import create_general_node
from prompts.system import GENERAL_SYSTEM_PROMPT
from prompts.tasks import GENERAL_RESPONSE_TASK


def test_general_node_uses_latest_message_with_general_prompts() -> None:
    """ترسل العقدة العامة أحدث رسالة بموجهات الدردشة الحرة."""
    received: list[dict] = []

    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        received.append(
            {
                "payload": json.loads(message),
                "system": system_prompt,
                "temperature": temperature,
            }
        )
        return "رد حر"

    node = create_general_node(fake_generate)
    result = asyncio.run(node({"messages": ["قديمة", "كيف حالك؟"]}))

    assert received == [
        {
            "payload": {
                "message": "كيف حالك؟",
                "context": {},
                "task": GENERAL_RESPONSE_TASK,
                "role": "general_assistant",
            },
            "system": GENERAL_SYSTEM_PROMPT,
            "temperature": 0.7,
        }
    ]
    assert result == {"response": "رد حر"}
