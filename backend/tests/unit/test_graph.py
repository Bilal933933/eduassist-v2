"""اختبارات الرسم الرئيسي وعقده ومساراته."""
import asyncio
import json

from graph import build_graph, checkpoint_config
from orchestration.nodes import (
    ALLOWED_INTENTS,
    create_classification_node,
    create_greeting_node,
    quick_reply_node,
)
from prompts.tasks import (
    GENERAL_RESPONSE_TASK,
    GREETING_RESPONSE_TASK,
    INTENT_CLASSIFICATION_TASK,
    RECALL_TASK,
)


def test_greeting_node_uses_model_without_mutating_state() -> None:
    """عقدة الترحيب تمرر المهمة للنموذج ولا تعدل الحالة المدخلة."""
    received: list[dict] = []

    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt
        received.append({"payload": json.loads(message), "temperature": temperature})
        return "أهلًا بك، كيف يمكنني مساعدتك؟"

    greeting_node = create_greeting_node(fake_generate)
    state = {"messages": ["مرحبًا"], "user_id": "user-1"}
    snapshot = dict(state)
    assert asyncio.run(greeting_node(state)) == {
        "response": "أهلًا بك، كيف يمكنني مساعدتك؟"
    }
    assert received == [
        {
            "payload": {
                "message": "مرحبًا",
                "context": {},
                "task": GREETING_RESPONSE_TASK,
                "role": "educational_assistant",
            },
            "temperature": 0.3,
        }
    ]
    assert state == snapshot


def test_classification_node_routes_supported_intents_without_mutation() -> None:
    """عقدة التصنيف تميز المسارات البسيطة ولا تعدل الحالة."""
    cases = [
        ("السَّلَامُ عَلَيْكُمْ!", "greeting"),
        ("شكرًا لك", "quick_reply"),
        ("اشرح المفعول به", "generation"),
        ("كيف حالك اليوم؟", "general"),
    ]
    for message, expected_intent in cases:
        async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
            assert choices == ALLOWED_INTENTS
            payload = json.loads(prompt)
            assert payload["message"] == message
            assert payload["task"].startswith(INTENT_CLASSIFICATION_TASK)
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
        if json.loads(message)["task"] == GREETING_RESPONSE_TASK:
            return "أهلًا بك، كيف يمكنني مساعدتك؟"
        return f"رد النموذج: {message}"

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = choices
        message = json.loads(prompt)["message"]
        return {
            "مرحبًا": "greeting",
            "تمام": "quick_reply",
            "كيف حالك؟": "general",
        }.get(message, "generation")

    cases = [
        ("مرحبًا", "greeting", "أهلًا بك، كيف يمكنني مساعدتك؟"),
        ("تمام", "quick_reply", "يسعدني ذلك، وأنا جاهز لمساعدتك."),
        (
            "اشرح النحو",
            "generation",
            'رد النموذج: {"message":"اشرح النحو","context":{},'
            '"task":"answer","role":"educational_assistant"}',
        ),
        (
            "كيف حالك؟",
            "general",
            "رد النموذج: "
            + json.dumps(
                {
                    "message": "كيف حالك؟",
                    "context": {},
                    "task": GENERAL_RESPONSE_TASK,
                    "role": "general_assistant",
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
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


def test_graph_routes_recall_through_summarize_to_generation() -> None:
    """نية التذكر تمر بالتلخيص قبل التوليد مع تمرير الملخص."""
    seen: list[dict] = []

    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt, temperature
        payload = json.loads(message)
        seen.append(payload)
        if payload["task"] == RECALL_TASK:
            return "كنا نتحدث عن المفعول به"
        return f"الإجابة بناء على: {payload['context'].get('summary', '')}"

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "recall"

    assistant_graph = build_graph(
        call_model=fake_generate,
        classify_intent=fake_classify,
    )
    result = asyncio.run(
        assistant_graph.ainvoke(
            {"messages": ["ما الذي كنا نتحدث عنه"], "user_id": "user-1"},
            checkpoint_config("user-1", "recall-conv"),
        )
    )

    assert result["intent"] == "recall"
    assert result["response"] == "الإجابة بناء على: كنا نتحدث عن المفعول به"
    assert any(entry["task"] == RECALL_TASK for entry in seen)


def test_abuse_node_escalates_count_without_mutating_state() -> None:
    """عقدة الإساءة ترفع العد في الحالة ولا تعدل المدخلات."""
    from orchestration.nodes import create_abuse_node

    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = message, system_prompt, temperature
        return "رد مهذب"

    abuse_node = create_abuse_node(fake_generate)
    state = {"messages": ["إساءة"], "user_id": "user-1", "abuse_count": 1}
    snapshot = dict(state)

    result = asyncio.run(abuse_node(state))

    assert result == {"response": "رد مهذب", "abuse_count": 2}
    assert state == snapshot


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
