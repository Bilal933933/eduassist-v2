"""اختبارات عقدة التوليد المحقونة."""

import asyncio

from orchestration.nodes.student.generation import create_generation_node


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

    assert received == [
        '{"message":"حديثة","context":{},"task":"answer",'
        '"role":"educational_assistant"}'
    ]
    assert result == {"response": "رد مولد"}
