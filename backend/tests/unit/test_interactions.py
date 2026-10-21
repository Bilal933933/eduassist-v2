"""اختبارات تمثيل الرسالة المنظم وبطاقة استكمال البيانات."""
import asyncio
import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.schemas.chat import ChatRequest
from graph import build_graph, checkpoint_config
from orchestration.graphs.roles import _route_after_classify
from orchestration.interactions.schema import Interaction
from orchestration.interactions.slots import (
    answers_as_message,
    build_questions,
    merge_answers,
    missing_slots,
)
from orchestration.nodes.shared import create_classification_node, clarify_node
from orchestration.nodes.shared.classification import TEACHER_INTENTS
from orchestration.nodes.teacher.lesson_prep_node import _duration_minutes


def test_grade_is_the_only_missing_slot_for_lesson_prep() -> None:
    """العنوان المعروف يترك الصف وحده حاجبًا."""
    state = {
        "intent": "lesson_prep",
        "properties": {"topic": "Present Simple"},
        "context": {},
    }

    assert missing_slots(state) == ["grade"]
    questions = build_questions(state)
    assert len(questions) == 1
    assert questions[0].slot == "grade"
    assert len(questions[0].options) == 6


def test_context_grade_resolves_without_asking() -> None:
    """صف المعلم المعروف من الملف يُغني عن السؤال."""
    state = {
        "intent": "lesson_prep",
        "properties": {"topic": "Present Simple"},
        "context": {"grade": "الأول الثانوي"},
    }

    assert missing_slots(state) == []


def test_merge_answers_rejects_missing_required_slot() -> None:
    """لا تُقبل إجابة ناقصة لحقل مطلوب."""
    questions = build_questions(
        {"intent": "lesson_prep", "properties": {"topic": "Present Simple"}}
    )

    with pytest.raises(ValueError):
        merge_answers(questions, {})


def test_merge_answers_filters_unknown_slots() -> None:
    """الإجابات تقتصر على أسئلة البطاقة."""
    questions = build_questions(
        {"intent": "lesson_prep", "properties": {"topic": "Present Simple"}}
    )

    merged = merge_answers(questions, {"grade": "الأول الثانوي", "x": "y"})
    assert merged == {"grade": "الأول الثانوي"}
    assert "الأول الثانوي" in answers_as_message(questions, merged)


def test_clarify_node_emits_open_interaction() -> None:
    """العقدة تعيد بطاقة مفتوحة وخصائص الطلب."""
    state = {
        "intent": "lesson_prep",
        "properties": {"topic": "Present Simple"},
        "context": {},
        "metadata": None,
    }

    result = clarify_node(state)
    interaction = Interaction.model_validate(result["interaction"])

    assert interaction.status == "open"
    assert interaction.properties["topic"] == "Present Simple"
    assert interaction.questions[0].slot == "grade"
    assert result["metadata"]["missing_slots"] == ["grade"]


def test_route_after_classify_sends_missing_slots_to_clarify() -> None:
    """التوجيه لا يمر بالبطاقة إلا في المسار المنظم."""
    state = {
        "intent": "lesson_prep",
        "properties": {"topic": "Present Simple"},
        "properties_ready": True,
        "context": {},
    }
    assert _route_after_classify(state) == "clarify"

    state["properties_ready"] = False
    assert _route_after_classify(state) == "lesson_prep"


def test_classification_uses_structured_interpretation() -> None:
    """المفسر المنظم يغني عن مصنف Enum ويحفظ الخصائص."""
    message = "اشرح Present Simple"

    async def classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        raise AssertionError("يجب ألا يعمل المصنف القديم")

    async def interpret(prompt: str, choices: tuple[str, ...]) -> dict:
        _ = prompt, choices
        return {
            "message": {
                "text": message,
                "intent": "lesson_prep",
                "properties": {"topic": "Present Simple"},
            }
        }

    node = create_classification_node(classify, TEACHER_INTENTS, interpret)
    result = asyncio.run(
        node(
            {
                "messages": [message],
                "user_role": "teacher",
                "context": {},
            }
        )
    )

    assert result["intent"] == "lesson_prep"
    assert result["properties"] == {"topic": "Present Simple"}
    assert result["properties_ready"] is True


def test_classification_rejects_mismatched_structured_text() -> None:
    """نص التفسير يجب أن يطابق رسالة المستخدم حرفيًا."""
    message = "اشرح Present Simple"

    async def classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "generation"

    async def interpret(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return json.dumps(
            {
                "message": {
                    "text": "رسالة أخرى",
                    "intent": "lesson_prep",
                    "properties": {"topic": "Present Simple"},
                }
            }
        )

    node = create_classification_node(classify, TEACHER_INTENTS, interpret)
    result = asyncio.run(
        node(
            {
                "messages": [message],
                "user_role": "teacher",
                "context": {},
            }
        )
    )

    assert result["intent"] == "generation"
    assert result["properties_ready"] is False


def test_classification_resumes_answered_interaction() -> None:
    """إجابات البطاقة تُستأنف بلا استدعاء النموذج."""
    message = "ما عنوان الدرس الذي تريده؟ Present Simple، لأي صف تريد هذه الخطة؟ الأول الثانوي"

    async def classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        raise AssertionError("يجب ألا يعمل المصنف عند الاستئناف")

    node = create_classification_node(classify, TEACHER_INTENTS)
    result = asyncio.run(
        node(
            {
                "messages": [message],
                "user_role": "teacher",
                "context": {
                    "interaction_resume": {
                        "intent": "lesson_prep",
                        "properties": {
                            "topic": "Present Simple",
                            "grade": "الأول الثانوي",
                        },
                        "message": message,
                    }
                },
            }
        )
    )

    assert result["intent"] == "lesson_prep"
    assert result["properties"]["grade"] == "الأول الثانوي"
    assert result["properties_ready"] is True


def test_teacher_graph_stops_at_clarify_when_grade_is_missing() -> None:
    """الرسم الكامل يعيد بطاقة الصف بلا تشغيل خطة الدرس."""
    message = "حضّر خطة لدرس Present Simple"

    async def classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        raise AssertionError("يجب ألا يعمل المصنف القديم")

    async def interpret(prompt: str, choices: tuple[str, ...]) -> dict:
        _ = prompt, choices
        return {
            "message": {
                "text": message,
                "intent": "lesson_prep",
                "properties": {"topic": "Present Simple"},
            }
        }

    graph = build_graph(
        call_model=AsyncMock(),
        classify_intent=classify,
        interpret_intent=interpret,
    )
    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [message],
                "user_id": "teacher-clarify",
                "user_role": "teacher",
                "context": {},
            },
            checkpoint_config("teacher-clarify", str(uuid4())),
        )
    )

    interaction = Interaction.model_validate(result["interaction"])
    assert result["intent"] == "lesson_prep"
    assert interaction.status == "open"
    assert [question.slot for question in interaction.questions] == ["grade"]


def test_duration_defaults_and_accepts_valid_values() -> None:
    """المدة الصالحة تُحترم، وغيرها يعود إلى 45 دقيقة."""
    assert _duration_minutes({}) == 45
    assert _duration_minutes({"duration_minutes": 60}) == 60
    assert _duration_minutes({"duration_minutes": "30"}) == 30
    assert _duration_minutes({"duration_minutes": 5}) == 45
    assert _duration_minutes({"duration_minutes": True}) == 45


def test_interpreted_message_coerces_missing_properties() -> None:
    """غياب properties لا يُفشل التفسير."""
    from orchestration.interactions.schema import InterpretedMessage

    message = InterpretedMessage.model_validate(
        {
            "text": "اشرح Present Simple",
            "intent": "lesson_prep",
            "properties": None,
        }
    )

    assert message.properties == {}


def test_chat_request_accepts_interaction_answer() -> None:
    """طلب الإجابة يتطلب بطاقة وإجابات غير فارغة."""
    request = ChatRequest(
        conversation_id=uuid4(),
        interaction_id=uuid4(),
        answers={"grade": "الأول الثانوي"},
        action="answer",
    )

    assert request.answers == {"grade": "الأول الثانوي"}


def test_chat_request_rejects_dismiss_without_interaction() -> None:
    """الإهمال بلا بطاقة غير صالح."""
    with pytest.raises(ValidationError):
        ChatRequest(conversation_id=uuid4(), action="dismiss")


def test_chat_request_rejects_answer_without_answers() -> None:
    """الإجابة بلا قيم غير صالحة."""
    with pytest.raises(ValidationError):
        ChatRequest(
            conversation_id=uuid4(),
            interaction_id=uuid4(),
            action="answer",
        )
