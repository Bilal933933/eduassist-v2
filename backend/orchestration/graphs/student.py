"""مسار الطالب: الرسم التعليمي."""

from collections.abc import Awaitable, Callable

from orchestration.graphs.roles import build_role_graph
from retrieval.service import RetrievalService


def build_student_graph(
    *,
    call_model: Callable[[str, str, float], Awaitable[str]],
    classify_intent: Callable[[str, tuple[str, ...]], Awaitable[str]],
    interpret_intent: (
        Callable[[str, tuple[str, ...]], Awaitable[dict | str]] | None
    ) = None,
    retrieval_service: RetrievalService | None = None,
):
    """تجميع عقد مسار الطالب مع استرجاع مراجع الإجابة."""
    return build_role_graph(
        role="student",
        call_model=call_model,
        classify_intent=classify_intent,
        interpret_intent=interpret_intent,
        retrieval_service=retrieval_service,
    )
