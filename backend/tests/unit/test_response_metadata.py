"""اختبارات عقد ميتا ديتا مصدر الرد ومسار تنفيذ العقد."""

import asyncio

from orchestration.nodes.shared import (
    create_abuse_node,
    create_classification_node,
    create_general_node,
    create_greeting_node,
    create_summarize_node,
    quick_reply_node,
)
from orchestration.nodes.shared.classification import STUDENT_INTENTS
from orchestration.nodes.student.generation import create_generation_node
from orchestration.nodes.teacher.generation import create_teacher_generation_node
from orchestration.state import append_node


async def _fake_generate(message: str, system_prompt: str, temperature: float) -> str:
    """نموذج وهمي يعيد ردًا ثابتًا."""
    _ = message, system_prompt, temperature
    return "رد"


async def _fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
    """مصنّف وهمي يعيد نية التوليد."""
    _ = prompt, choices
    return "generation"


def test_append_node_keeps_previous_keys_and_extends_path() -> None:
    """المساعد يدمج المفاتيح السابقة ويضيف العقدة إلى مسار التنفيذ."""
    metadata = append_node({"intent": "general"}, "classify")
    metadata = append_node(metadata, "generation", handled_by="student_generation_node")
    assert metadata["intent"] == "general"
    assert metadata["handled_by"] == "student_generation_node"
    assert metadata["nodes_path"] == ["classify", "generation"]


def test_append_node_starts_path_without_previous_metadata() -> None:
    """المساعد يبدأ المسار من عقدة واحدة بلا ميتا داتا سابقة."""
    assert append_node(None, "greeting")["nodes_path"] == ["greeting"]


def test_classification_node_records_intent_and_path() -> None:
    """عقدة التصنيف توثّق النية والعقدة التي صنّفت."""
    node = create_classification_node(_fake_classify, STUDENT_INTENTS)
    result = asyncio.run(node({"messages": ["سؤال"]}))
    assert result["metadata"]["intent"] == "generation"
    assert result["metadata"]["classified_by"] == "classification_node"
    assert result["metadata"]["nodes_path"] == ["classify"]


def test_student_generation_node_records_source_and_role() -> None:
    """عقدة توليد الطالب توثّق مصدر الرد ودور النموذج."""
    node = create_generation_node(_fake_generate)
    result = asyncio.run(node({"messages": ["سؤال"]}))
    assert result["metadata"]["handled_by"] == "student_generation_node"
    assert result["metadata"]["response_source"] == "llm"
    assert result["metadata"]["generator_role"] == "educational_assistant"


def test_teacher_generation_node_records_source_and_role() -> None:
    """عقدة توليد المعلم توثّق مصدر الرد ودور النموذج."""
    node = create_teacher_generation_node(_fake_generate)
    result = asyncio.run(node({"messages": ["سؤال"]}))
    assert result["metadata"]["handled_by"] == "teacher_generation_node"
    assert result["metadata"]["generator_role"] == "teacher_assistant"


def test_recall_path_marks_recalled_reply() -> None:
    """مسار الذاكرة يوسم الرد بأنه مبني على تلخيص السابق."""
    node = create_generation_node(_fake_generate)
    result = asyncio.run(node({"messages": ["سؤال"], "summary": "ملخص"}))
    assert result["metadata"]["recalled"] is True


def test_general_greeting_and_abuse_nodes_record_handled_by() -> None:
    """كل عقدة تنتج ردًا تسمّي نفسها في الميتا داتا."""
    general = asyncio.run(create_general_node(_fake_generate)({"messages": ["مرحبا"]}))
    greeting = asyncio.run(create_greeting_node(_fake_generate)({"messages": ["مرحبا"]}))
    abuse = asyncio.run(create_abuse_node(_fake_generate)({"messages": ["سوء"]}))
    assert general["metadata"]["handled_by"] == "general_node"
    assert greeting["metadata"]["handled_by"] == "greeting_node"
    assert abuse["metadata"]["handled_by"] == "abuse_node"
    assert abuse["metadata"]["abuse_count"] == 1


def test_summarize_node_records_handled_by() -> None:
    """عقدة التلخيص توثّق نفسها لتمييز مسار الذاكرة."""
    node = create_summarize_node(_fake_generate)
    result = asyncio.run(node({"messages": ["سؤال"]}))
    assert result["metadata"]["handled_by"] == "summarize_node"


def test_quick_reply_node_marks_template_source() -> None:
    """الرد السريع حتمي فيصلك مصدره نصًا جاهزًا لا نموذجًا."""
    result = quick_reply_node({"messages": ["شكرا"]})
    assert result["metadata"]["response_source"] == "template"
    assert result["metadata"]["nodes_path"] == ["quick_reply"]
