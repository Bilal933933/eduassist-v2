"""مسار المعلم: مسار الطالب مع عقدة تحضير الدرس وتوليد مخصص."""

from collections.abc import Awaitable, Callable

from orchestration.graphs.roles import build_role_graph
from retrieval.service import RetrievalService


def build_teacher_graph(
    *,
    call_model: Callable[[str, str, float], Awaitable[str]],
    classify_intent: Callable[[str, tuple[str, ...]], Awaitable[str]],
    retrieval_service: RetrievalService | None = None,
):
    """تجميع عقد مسار المعلم في رسم فرعي بلا نقاط تفتيش."""
    return build_role_graph(
        role="teacher",
        call_model=call_model,
        classify_intent=classify_intent,
        retrieval_service=retrieval_service,
    )
