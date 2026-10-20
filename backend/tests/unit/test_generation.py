"""اختبارات عقدة التوليد المحقونة."""

import asyncio
import json

from orchestration.nodes.student.generation import create_generation_node
from prompts.tasks import GENERATION_TASK


def test_generation_node_uses_latest_message() -> None:
    """ترسل عقدة التوليد أحدث رسالة فقط إلى النموذج."""
    received: list[str] = []

    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt, temperature
        received.append(message)
        return "رد مولد"

    node = create_generation_node(fake_generate)
    result = asyncio.run(node({"messages": ["قديمة", "حديثة"]}))

    assert len(received) == 1
    payload = json.loads(received[0])
    assert payload == {
        "message": "حديثة",
        "context": {},
        "task": GENERATION_TASK,
        "role": "educational_assistant",
    }
    assert result["response"] == "رد مولد"
    assert result["metadata"]["handled_by"] == "student_generation_node"
    assert result["metadata"]["generator_role"] == "educational_assistant"
    assert result["metadata"]["recalled"] is False
