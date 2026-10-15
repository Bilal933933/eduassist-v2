"""اختبارات الرسم الرئيسي وعقده ومساراته."""
import asyncio
import json

from graph import GREETING_TEXT, build_graph, checkpoint_config, greeting_node
from orchestration.nodes import (
    ALLOWED_INTENTS,
    create_classification_node,
    quick_reply_node,
)


def test_greeting_node_is_pure() -> None:
    """عقدة الترحيب لا تعدل الحالة المدخلة."""
    state = {"messages": ["مرحبًا"], "user_id": "user-1"}
    snapshot = dict(state)
    assert greeting_node(state) == {"response": GREETING_TEXT}
    assert state == snapshot


def test_classification_node_routes_supported_intents_without_mutation() -> None:
    """عقدة التصنيف تميز المسارات البسيطة ولا تعدل الحالة."""
    cases = [
        ("السَّلَامُ عَلَيْكُمْ!", "greeting"),
        ("شكرًا لك", "quick_reply"),
        ("اشرح المفعول به", "generation"),
    ]
    for message, expected_intent in cases:
        async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
            assert choices == ALLOWED_INTENTS
            assert message in prompt
            return expected_intent

        classify_node = create_classification_node(fake_classify)
        state = {"messages": [message], "user_id": "user-1"}
        snapshot = {"messages": [message], "user_id": "user-1"}
        assert asyncio.run(classify_node(state)) == {"intent": expected_intent}
        assert state == snapshot


def test_classification_node_uses_generation_for_invalid_result() -> None:
    """توجه العقدة النتيجة غير المعروفة إلى مسار التوليد الآمن."""
    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "unknown"

    classify_node = create_classification_node(fake_classify)

    result = asyncio.run(classify_node({"messages": ["رسالة"]}))

    assert result == {"intent": "generation"}


def test_quick_reply_node_returns_specific_response() -> None:
    """عقدة الرد السريع لا تعتمد على تطابق نص الرسالة."""
    result = quick_reply_node({"messages": ["متشكر جدًا"]})
    assert result == {"response": "يسعدني ذلك، وأنا جاهز لمساعدتك."}


def test_graph_routes_greeting_quick_reply_and_generation_message() -> None:
    """الرسم يمرر كل نية إلى عقدة الرد الصحيحة."""
    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt, temperature
        return f"رد النموذج: {message}"

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = choices
        message = json.loads(prompt)["message"]
        return {
            "مرحبًا": "greeting",
            "تمام": "quick_reply",
        }.get(message, "generation")

    cases = [
        ("مرحبًا", "greeting", GREETING_TEXT),
        ("تمام", "quick_reply", "يسعدني ذلك، وأنا جاهز لمساعدتك."),
        (
            "اشرح النحو",
            "generation",
            'رد النموذج: {"message":"اشرح النحو","context":{},'
            '"task":"answer","role":"educational_assistant"}',
        ),
    ]
    for index, (message, expected_intent, expected_response) in enumerate(cases):
        assistant_graph = build_graph(
            call_model=fake_generate,
            classify_intent=fake_classify,
        )
        result = asyncio.run(
            assistant_graph.ainvoke(
                {"messages": [message], "user_id": "user-1"},
                checkpoint_config("user-1", f"conversation-{index}"),
            )
        )
        assert result["intent"] == expected_intent
        assert result["response"] == expected_response


def test_checkpoint_is_isolated_by_user_and_conversation() -> None:
    """لا تتشارك المحادثات الحالة بين مستخدمين مختلفين."""
    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt, temperature
        return message

    async def run_isolated_calls() -> dict:
        async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
            _ = prompt, choices
            return "generation"

        assistant_graph = build_graph(
            call_model=fake_generate,
            classify_intent=fake_classify,
        )
        await assistant_graph.ainvoke(
            {"messages": ["الأولى"], "user_id": "user-1"},
            checkpoint_config("user-1", "shared"),
        )
        return await assistant_graph.ainvoke(
            {"messages": ["الثانية"], "user_id": "user-2"},
            checkpoint_config("user-2", "shared"),
        )

    result = asyncio.run(run_isolated_calls())
    assert result["messages"] == ["الثانية"]
