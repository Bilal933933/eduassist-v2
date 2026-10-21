"""اختبارات الرسم الرئيسي وعقده ومساراته."""
import asyncio
import json

from graph import build_graph, checkpoint_config
from orchestration.nodes import (
    STUDENT_INTENTS,
    TEACHER_INTENTS,
    create_classification_node,
    create_greeting_node,
    quick_reply_node,
)
from orchestration.nodes.shared.retrieval import MAX_CHUNK_CHARS, format_chunks
from prompts.tasks import (
    GENERAL_RESPONSE_TASK,
    GENERATION_TASK,
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
    result = asyncio.run(greeting_node(state))
    assert result["response"] == "أهلًا بك، كيف يمكنني مساعدتك؟"
    assert result["metadata"]["handled_by"] == "greeting_node"
    assert result["metadata"]["nodes_path"] == ["greeting"]
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
            assert choices == STUDENT_INTENTS
            payload = json.loads(prompt)
            assert payload["message"] == message
            assert payload["task"].startswith(INTENT_CLASSIFICATION_TASK)
            return expected_intent

        classify_node = create_classification_node(fake_classify, STUDENT_INTENTS)
        state = {"messages": [message], "user_id": "user-1"}
        snapshot = {"messages": [message], "user_id": "user-1"}
        result = asyncio.run(classify_node(state))
        assert result["intent"] == expected_intent
        assert result["metadata"]["intent"] == expected_intent
        assert result["metadata"]["classified_by"] == "classification_node"
        assert result["metadata"]["nodes_path"] == ["classify"]
        assert state == snapshot


def test_classification_prompt_carries_saved_lesson_context() -> None:
    """المصنّف يرى وجود الخطة وموضوعها ليؤدي الضمائر إلى تعديل الخطة."""
    seen: list[dict] = []

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = choices
        seen.append(json.loads(prompt))
        return "lesson_refine"

    classify_node = create_classification_node(fake_classify, TEACHER_INTENTS)
    asyncio.run(
        classify_node(
            {
                "messages": ["وسّعه"],
                "intent": "generation",
                "lesson_plan": "خطة محفوظة",
                "lesson_topic": "المفعول به",
                "metadata": {},
            }
        )
    )

    context = seen[0]["context"]
    assert context["lesson_plan_available"] is True
    assert context["lesson_topic"] == "المفعول به"


def test_classification_node_falls_back_to_generation_on_failure() -> None:
    """فشل المصنف لا يمنع الرد ويحوّل الرسالة لمسار التوليد الآمن."""
    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        raise TimeoutError("down")

    classify_node = create_classification_node(fake_classify, STUDENT_INTENTS)

    result = asyncio.run(classify_node({"messages": ["رسالة"]}))

    assert result["intent"] == "generation"
    assert result["metadata"]["classifier_failed"] is True


def test_classification_node_uses_generation_for_invalid_result() -> None:
    """توجه العقدة النتيجة غير المعروفة إلى مسار التوليد الآمن."""
    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "unknown"

    classify_node = create_classification_node(fake_classify, STUDENT_INTENTS)

    result = asyncio.run(classify_node({"messages": ["رسالة"]}))

    assert result["intent"] == "generation"
    assert result["metadata"]["intent"] == "generation"


def test_quick_reply_node_returns_specific_response() -> None:
    """عقدة الرد السريع لا تعتمد على تطابق نص الرسالة."""
    result = quick_reply_node({"messages": ["متشكر جدًا"]})
    assert result["response"] == "يسعدني ذلك، وأنا جاهز لمساعدتك."
    assert result["metadata"]["handled_by"] == "quick_reply_node"
    assert result["metadata"]["response_source"] == "template"


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
            "رد النموذج: "
            + json.dumps(
                {
                    "message": "اشرح النحو",
                    "context": {},
                    "task": GENERATION_TASK,
                    "role": "educational_assistant",
                },
                ensure_ascii=False,
                separators=(",", ":"),
            ),
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


class _FakeRetrieval:
    """خدمة استرجاع وهمية تنجح أو تفشل."""

    def __init__(self, chunks: list[dict] | None = None) -> None:
        self._chunks = chunks or []
        self._error = None

    async def search_hybrid(
        self,
        query: str,
        subject: str | None = None,
        grade: str | None = None,
    ) -> list[dict]:
        _ = query, subject, grade
        if self._error is not None:
            raise self._error
        return self._chunks


def test_student_generation_uses_retrieved_references() -> None:
    """مسار الطالب يمر بالاسترجاع ويحقن المراجع في سياق التوليد."""
    seen: list[dict] = []

    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt, temperature
        seen.append(json.loads(message))
        return "رد"

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "generation"

    assistant_graph = build_graph(
        call_model=fake_generate,
        classify_intent=fake_classify,
        retrieval_service=_FakeRetrieval(
            [{"content": "قاعدة نحوية موثوقة", "source_type": "curriculum"}]
        ),
    )
    result = asyncio.run(
        assistant_graph.ainvoke(
            {
                "messages": ["اشرح المفعول به"],
                "user_id": "user-1",
                "user_role": "student",
                "metadata": {},
                "summary": "",
                "retrieved_chunks": [],
            },
            checkpoint_config("user-1", "student-retrieval"),
        )
    )

    generation = next(p for p in seen if p["task"] == GENERATION_TASK)
    assert "قاعدة نحوية موثوقة" in generation["context"]["references"]
    assert result["metadata"]["nodes_path"] == ["classify", "retrieve", "generation"]


def test_student_generation_survives_retrieval_failure() -> None:
    """فشل الاسترجاع لا يمنع الرد ولا يدّعي استخدام مراجع."""
    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = message, system_prompt, temperature
        return "رد"

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "generation"

    retrieval = _FakeRetrieval()
    retrieval._error = RuntimeError("down")
    assistant_graph = build_graph(
        call_model=fake_generate,
        classify_intent=fake_classify,
        retrieval_service=retrieval,
    )
    result = asyncio.run(
        assistant_graph.ainvoke(
            {
                "messages": ["اشرح المفعول به"],
                "user_id": "user-1",
                "user_role": "student",
                "metadata": {},
                "summary": "",
                "retrieved_chunks": [],
            },
            checkpoint_config("user-1", "student-retrieval-down"),
        )
    )

    assert result["response"] == "رد"
    assert result["metadata"]["retrieval_used"] is False


def test_format_chunks_caps_chunk_length() -> None:
    """المقطع الطويل يُقص فلا يتضخم موجّه الوكيل."""
    text = format_chunks([{"content": "ا" * 5000, "source_type": "doc"}])
    assert text.startswith("- [doc] ")
    assert len(text) == len("- [doc] ") + MAX_CHUNK_CHARS


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

    assert result["response"] == "رد مهذب"
    assert result["abuse_count"] == 2
    assert result["metadata"]["handled_by"] == "abuse_node"
    assert result["metadata"]["abuse_count"] == 2
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


def test_metadata_path_does_not_accumulate_across_turns() -> None:
    """ميتا ديتا الدور الجديد لا ترث مسار تنفيذ الدور السابق."""

    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt, temperature
        return message

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "generation"

    async def scenario() -> dict:
        assistant_graph = build_graph(
            call_model=fake_generate,
            classify_intent=fake_classify,
        )
        config = checkpoint_config("user-1", "metadata-path")
        await assistant_graph.ainvoke(
            {
                "messages": ["الأولى"],
                "user_id": "user-1",
                "user_role": "student",
                "metadata": {},
            },
            config,
        )
        return await assistant_graph.ainvoke(
            {
                "messages": ["الثانية"],
                "user_id": "user-1",
                "user_role": "student",
                "metadata": {},
            },
            config,
        )

    result = asyncio.run(scenario())
    assert result["metadata"]["nodes_path"] == ["classify", "retrieve", "generation"]


def test_summary_does_not_leak_across_turns() -> None:
    """ملخص دور التذكر لا يبقى في سياق توليد الدور التالي."""

    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt, temperature
        payload = json.loads(message)
        if payload["task"] == RECALL_TASK:
            return "كنا نتحدث عن المفعول به"
        return "رد"

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = choices
        message = json.loads(prompt)["message"]
        return "recall" if message == "ما الذي كنا نتحدث عنه" else "generation"

    async def scenario() -> dict:
        assistant_graph = build_graph(
            call_model=fake_generate,
            classify_intent=fake_classify,
        )
        config = checkpoint_config("user-1", "summary-leak")
        await assistant_graph.ainvoke(
            {
                "messages": ["ما الذي كنا نتحدث عنه"],
                "user_id": "user-1",
                "user_role": "student",
                "metadata": {},
                "summary": "",
            },
            config,
        )
        return await assistant_graph.ainvoke(
            {
                "messages": ["اشرح المفعول به"],
                "user_id": "user-1",
                "user_role": "student",
                "metadata": {},
                "summary": "",
            },
            config,
        )

    result = asyncio.run(scenario())
    assert result["intent"] == "generation"
    assert result["metadata"]["recalled"] is False


def test_lesson_refine_uses_saved_plan_from_checkpoint() -> None:
    """تعديل خطة لاحقة يعيد استخدام الموضوع وآخر خطة من نقطة التفتيش."""
    prompts: list[dict] = []

    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt, temperature
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            payload = {"task": message}
        prompts.append(payload)
        task = payload["task"]
        if "قيّم جودة خطة الدرس" in task:
            return '{"score": 0.9, "section": null}'
        if "جمّع الأقسام التالية" in task:
            return "خطة نهائية"
        return "قسم"

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = choices
        message = json.loads(prompt)["message"]
        if "كان وأخواتها" in message:
            return "lesson_prep"
        return "lesson_refine"

    async def scenario() -> tuple[dict, dict]:
        assistant_graph = build_graph(
            call_model=fake_generate,
            classify_intent=fake_classify,
        )
        config = checkpoint_config("user-1", "lesson-refine")
        first = await assistant_graph.ainvoke(
            {
                "messages": ["حضّر درس كان وأخواتها"],
                "user_id": "user-1",
                "user_role": "teacher",
                "metadata": {},
                "summary": "",
                "retrieved_chunks": [],
            },
            config,
        )
        prompts.clear()
        second = await assistant_graph.ainvoke(
            {
                "messages": ["وسّع الأهداف"],
                "user_id": "user-1",
                "user_role": "teacher",
                "metadata": {},
                "summary": "",
                "retrieved_chunks": [],
            },
            config,
        )
        return first, second

    first, second = asyncio.run(scenario())

    assert first["lesson_topic"] == "حضّر درس كان وأخواتها"
    assert "basic_info" in first["lesson_sections"]
    assert second["intent"] == "lesson_refine"
    assert second["lesson_topic"] == "حضّر درس كان وأخواتها"
    assert second["lesson_sections"] == second["sections"]
    basic = next(p for p in prompts if "اكتب البيانات الأساسية" in p["task"])
    assert "حضّر درس كان وأخواتها" in basic["task"]
    assert "خطة نهائية" in basic["task"]


def test_lesson_refine_without_plan_asks_for_clarification() -> None:
    """تعديل بلا خطة في المحادثة لا يشغّل التحضير ولا يخترع درسًا."""
    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = message, system_prompt, temperature
        raise AssertionError("لا يجوز توليد خطة عند غياب الخطة السابقة")

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "lesson_refine"

    assistant_graph = build_graph(
        call_model=fake_generate,
        classify_intent=fake_classify,
    )
    result = asyncio.run(
        assistant_graph.ainvoke(
            {
                "messages": ["وسّع الأهداف"],
                "user_id": "user-1",
                "user_role": "teacher",
                "metadata": {},
                "summary": "",
                "retrieved_chunks": [],
            },
            checkpoint_config("user-1", "refine-without-plan"),
        )
    )

    assert "لا توجد خطة" in result["response"]
    assert result["metadata"]["refine_missing_plan"] is True
    assert result["metadata"]["nodes_path"] == ["classify", "lesson_prep"]


def test_checkpoint_accumulates_messages_without_subgraph_duplication() -> None:
    """نقطة التفتيش تجمع الرسائل دون أن يضيفها الرسم الفرعي مرة ثانية."""
    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt, temperature
        return message

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "generation"

    async def scenario() -> dict:
        assistant_graph = build_graph(
            call_model=fake_generate,
            classify_intent=fake_classify,
        )
        config = checkpoint_config("user-1", "accumulating")
        await assistant_graph.ainvoke(
            {"messages": ["الأولى"], "user_id": "user-1", "user_role": "student"},
            config,
        )
        return await assistant_graph.ainvoke(
            {"messages": ["الثانية"], "user_id": "user-1", "user_role": "student"},
            config,
        )

    result = asyncio.run(scenario())
    assert result["messages"] == ["الأولى", "الثانية"]
    assert result["user_role"] == "student"
