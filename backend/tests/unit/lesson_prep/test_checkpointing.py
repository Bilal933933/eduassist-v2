"""اختبارات سياسة حفظ اللقطات في الرسمين الأب والفرعي."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from orchestration.lesson_prep.graph import build_lesson_prep_subgraph

CallModel = Callable[[str, str, float], Awaitable[str]]


async def _fake_call_model(
    task: str, system_prompt: str, temperature: float
) -> str:
    _ = system_prompt, temperature
    return "محتوى تجريبي"


def test_lesson_prep_subgraph_does_not_persist_checkpoints() -> None:
    """الرسم الفرعي لا يكتب لقطات: حالته تعيش داخل استدعائه فقط."""
    subgraph = build_lesson_prep_subgraph(
        call_model=_fake_call_model,
        retrieval_service=None,
    )

    assert subgraph.checkpointer is False
