"""عقدة استرجاع مشتركة بين المسارين وتنسيق مراجعها."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from orchestration.state import AgentState, append_node
from retrieval.service import RetrievalService

logger = logging.getLogger("eduassist.retrieval.node")

# سقوف تمنع تضخم الموجّه: الاسترجاع الهجين قد يعيد مقاطع كاملة كثيرة.
MAX_CHUNK_CHARS = 700
MAX_TOTAL_CHARS = 6000
MAX_CHUNKS = 8


def format_chunks(chunks: list[dict[str, Any]]) -> str:
    """تنسيق نتائج الاسترجاع بنص محدود الطول يُمرَّر إلى الوكيل.

    نتائج المنهج تحمل المفتاح ``content`` ونتائج ويكيبيديا ``snippet``،
    فيُقرأ الاثنان حتى لا يصل الوكيل محتوى فارغًا.
    """
    lines: list[str] = []
    total = 0
    for chunk in chunks[:MAX_CHUNKS]:
        body = chunk.get("content") or chunk.get("snippet") or chunk.get("text") or ""
        body = str(body).strip()
        if not body:
            continue
        line = f"- [{chunk.get('source_type', 'unknown')}] {body[:MAX_CHUNK_CHARS]}"
        if total + len(line) > MAX_TOTAL_CHARS:
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines)


def create_retrieve_node(
    retrieval_service: RetrievalService | None,
) -> Callable[[AgentState], Awaitable[dict[str, Any]]]:
    """إنشاء عقدة استرجاع لا تُسقط الرد عند فشل خدمة الاسترجاع."""

    async def retrieve_node(state: AgentState) -> dict[str, Any]:
        query = state["messages"][-1]
        context = state.get("context", {})
        chunks: list[dict[str, Any]] = []
        if retrieval_service is not None:
            try:
                chunks = await retrieval_service.search_hybrid(
                    query=query,
                    subject=context.get("subject"),
                    grade=context.get("grade"),
                )
            except Exception as error:
                logger.warning("تعذر استرجاع مراجع الرد: %s", error)
        return {
            "retrieved_chunks": chunks,
            "metadata": append_node(
                state.get("metadata"),
                "retrieve",
                handled_by="retrieve_node",
                retrieval_used=bool(chunks),
                retrieved_count=len(chunks),
            ),
        }

    return retrieve_node
