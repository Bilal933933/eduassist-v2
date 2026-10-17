"""اختبارات توجيه الدور وبروفايل المعلم."""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from db.repositories.teacher_profile_repository import TeacherProfileRepository
from graph import build_graph, checkpoint_config
from orchestration.graphs.main import route_role
from services.chat_service import build_teacher_brief


def test_route_role_sends_teacher_with_brief_to_teacher() -> None:
    """المعلم ذو البروفايل يوجه لمساره."""
    state = {
        "messages": ["مرحبًا"],
        "user_role": "teacher",
        "context": {"teacher_brief": "المادة: النحو"},
    }
    assert route_role(state) == "teacher"


def test_route_role_falls_back_to_student_without_brief() -> None:
    """المعلم بلا بروفايل والطالب والقيم الغريبة ← مسار الطالب الآمن."""
    assert route_role({"messages": ["x"], "user_role": "teacher", "context": {}}) == (
        "student"
    )
    assert route_role({"messages": ["x"], "user_role": "student"}) == "student"
    assert route_role({"messages": ["x"]}) == "student"
    assert route_role({"messages": ["x"], "user_role": "admin"}) == "student"


def test_teacher_brief_is_compact_arabic_summary() -> None:
    """الخلاصة مضغوطة وتحتوي الحقول الثلاثة."""
    profile = SimpleNamespace(
        subject="النحو", class_name="الثالث ثانوي", students_note="30 طالبًا"
    )
    brief = build_teacher_brief(profile)

    assert "النحو" in brief and "الثالث ثانوي" in brief and "30 طالبًا" in brief
    assert len(brief) <= 200
    assert build_teacher_brief(None) == ""


def test_teacher_graph_injects_brief_into_generation() -> None:
    """توليد المعلم يحقن الخلاصة في السياق المرسل للنموذج."""
    received: list[dict] = []

    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt, temperature
        received.append(json.loads(message))
        return "رد المعلم"

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "generation"

    assistant_graph = build_graph(
        call_model=fake_generate,
        classify_intent=fake_classify,
    )
    result = asyncio.run(
        assistant_graph.ainvoke(
            {
                "messages": ["اشرح المبتدأ"],
                "user_id": "teacher-1",
                "user_role": "teacher",
                "context": {"teacher_brief": "المادة: النحو"},
            },
            checkpoint_config("teacher-1", "teacher-conv"),
        )
    )

    assert result["response"] == "رد المعلم"
    assert received[0]["context"]["teacher_brief"] == "المادة: النحو"
    assert received[0]["role"] == "teacher_assistant"


def test_teacher_without_brief_uses_student_path() -> None:
    """معلم بلا بروفايل يسلك مسار الطالب الآمن."""
    received: list[dict] = []

    async def fake_generate(
        message: str, system_prompt: str, temperature: float
    ) -> str:
        _ = system_prompt, temperature
        received.append(json.loads(message))
        return "رد الطالب"

    async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
        _ = prompt, choices
        return "generation"

    assistant_graph = build_graph(
        call_model=fake_generate,
        classify_intent=fake_classify,
    )
    result = asyncio.run(
        assistant_graph.ainvoke(
            {
                "messages": ["اشرح المبتدأ"],
                "user_id": "teacher-2",
                "user_role": "teacher",
                "context": {},
            },
            checkpoint_config("teacher-2", "fallback-conv"),
        )
    )

    assert result["response"] == "رد الطالب"
    assert received[0]["role"] == "educational_assistant"


def test_teacher_profile_repository_get_and_upsert() -> None:
    """المستودع يجلب البروفايل وينشئه أو يحدثه."""
    profile_id = uuid4()
    user_id = uuid4()

    async def run() -> None:
        session = Mock()
        existing = SimpleNamespace(
            id=profile_id,
            user_id=user_id,
            subject="قديم",
            class_name="قديم",
            students_note="قديم",
        )
        session.scalar = AsyncMock(side_effect=[None, existing])
        session.add = Mock()
        session.flush = AsyncMock()
        repository = TeacherProfileRepository(session)

        assert await repository.get_by_user(user_id) is None

        updated = await repository.upsert(
            user_id, "النحو", "الثالث ثانوي", "30 طالبًا"
        )

        assert updated.subject == "النحو"
        assert session.flush.await_count == 1

    asyncio.run(run())
