"""عقدة ملف الدرس المعرفي: جمع كل المصادر ثم توليفها موضوعيًا."""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from orchestration.state import AgentState, append_node
from prompts import get_prompt
from prompts.tasks.lesson_info import (
    LESSON_INFO_COMPOSE_TASK,
    LESSON_INFO_EXTRACT_TASK,
)
from retrieval.lesson_knowledge import (
    MAX_BATCHES,
    MAX_DIRECT_CHARS,
    coverage_missing,
    limit_sources,
    render_source,
    render_sources,
    split_batches,
)
from retrieval.service import RetrievalService

logger = logging.getLogger("eduassist.lesson_info")

CallModel = Callable[[str, str, float], Awaitable[str]]

# الأسئلة القصيرة التي تشير إلى الدرس المحفوظ بدل تكرار عنوانه.
_FOLLOWUP_PATTERN = re.compile(
    r"(هذا الدرس|نفس الدرس|الدرس نفسه|معلوماته|كل معلوماته|"
    r"أعدها|أعد لي|نظمها|لخصها|وسّعه)"
)

# استخراج عنوان الدرس من صيغة الطلب نفسها، فلا يُرسل «أعطني كل المعلومات»
# إلى ويكيبيديا أو البحث الدلالي بدل اسم الدرس.
_TOPIC_PREFIX = re.compile(
    r"^(?:أعطني|اعطني|أريد|اريد|أحتاج|احتاج|قدّم|قدم|اعرض|أعرض|"
    r"أرني|ارني|هات|اجمع|أعد|حضر|حضّر|جهز|جهّز|اكتب|أكتب|أعدد)"
    r"\s+(?:لي\s+)?(?:كل\s+)?"
    r"(?:(?:(?:ال)?معلومات|ملف|تحضير)\s+"
    r"(?:(?:عن|حول|بخصوص)\s+(?:درس(?:ًا|اً)?\s+)?|درس(?:ًا|اً)?\s+)"
    r"|درس(?:ًا|اً)?\s+)"
)
_TOPIC_LEAD = re.compile(
    r"^(?:كل\s+)?(?:(?:ال)?معلومات|ما\s+لديك)\s+"
    r"(?:(?:عن|حول|بخصوص)\s+|درس(?:ًا|اً)?\s+)"
    r"(?:درس(?:ًا|اً)?\s+)?"
)
_TOPIC_SUFFIX = re.compile(
    r"\s+(?:من\s+(?:كل|جميع)\s+(?:المصادر|الصفوف)|"
    r"ل(?:كل|جميع)\s+الصفوف|بالكامل|كاملة|كامل)\s*$"
)


def _clean_topic(message: str) -> str:
    """إزالة عبارات الطلب من الرسالة، مع إبقاء عنوان الدرس."""
    value = message.strip()
    prefixed = _TOPIC_PREFIX.sub("", value, count=1)
    if prefixed != value:
        value = prefixed
    else:
        value = _TOPIC_LEAD.sub("", value, count=1)
    value = _TOPIC_SUFFIX.sub("", value, count=1)
    return value.strip() or message.strip()


def _resolve_query(state: AgentState) -> str:
    """اختيار نص البحث: عنوان محفوظ للمتابعة، أو عنوان مستخرج من الطلب."""
    message = state["messages"][-1].strip()
    saved = (state.get("lesson_topic") or "").strip()
    if saved and len(message) <= 160 and _FOLLOWUP_PATTERN.search(message):
        return saved
    return _clean_topic(message)


def _pick_topic(
    sources: list[dict[str, Any]], query: str, saved: str
) -> str:
    """عنوان مختصر يُحفظ للمتابعة، لا نص الطلب الكامل.

    لا نأخذ عنوان أول صفحة ويكيبيديا عمياء؛ فقد يكون صفحة قريبة لا مطابقة.
    """
    for source in sources:
        if source.get("kind") != "curriculum":
            continue
        title = str(source.get("title") or "").strip()
        if title and (title in query or query in title):
            return title

    for source in sources:
        if source.get("kind") == "curriculum":
            continue
        title = str(source.get("title") or "").strip()
        if title and title == query:
            return title

    if saved:
        return saved
    return query if len(query) <= 80 else ""


def _empty_result(
    state: AgentState,
    response: str,
    *,
    response_source: str,
    **extra: Any,
) -> dict[str, Any]:
    """رد صريح عند تعذر المصادر، بلا نداء نموذج ولا اختلاق."""
    metadata = append_node(
        state.get("metadata"),
        "lesson_info",
        intent=state.get("intent"),
        handled_by="lesson_info_node",
        response_source=response_source,
        lesson_info=True,
        source_count=0,
        sources=[],
        grades=[],
        truncated=False,
        **extra,
    )
    result: dict[str, Any] = {"response": response, "metadata": metadata}
    if state.get("lesson_topic"):
        result["lesson_topic"] = state["lesson_topic"]
    return result


def _fallback_dossier(sources: list[dict[str, Any]]) -> str:
    """عرض المصادر منظمة إذا فشل التوليف، فلا يضيع المحتوى."""
    blocks = ["تعذر توليف ملف الدرس، وفيما يلي المصادر كما وردت:"]
    for index, source in enumerate(sources, start=1):
        blocks.append(render_source(source, index))
    return "\n\n".join(blocks)


def _append_missing_references(
    response: str, sources: list[dict[str, Any]]
) -> str:
    """إظهار أي مصدر لم يذكره النموذج حتى لا يغيب مصدر من الملف."""
    missing = coverage_missing(sources, response)
    if not missing:
        return response
    lines = [response, "", "**مصادر إضافية:**"]
    for source in missing:
        line = f"- {source.get('title')}"
        if source.get("url"):
            line += f" — {source['url']}"
        lines.append(line)
    return "\n".join(lines)


def create_lesson_info_node(
    *,
    call_model: CallModel,
    retrieval_service: RetrievalService | None,
):
    """إنشاء عقدة ملف الدرس للمعلم فقط."""

    async def lesson_info_node(state: AgentState) -> dict[str, Any]:
        if retrieval_service is None:
            return _empty_result(
                state,
                "خدمة المصادر غير متاحة الآن؛ لم أتمكن من جلب معلومات الدرس.",
                response_source="unavailable",
                retrieval_available=False,
            )

        query = _resolve_query(state)
        if not query:
            return _empty_result(
                state,
                "حدد عنوان الدرس الذي تريد جمع معلوماته.",
                response_source="clarification",
            )

        saved_topic = (state.get("lesson_topic") or "").strip()
        try:
            sources = await retrieval_service.search_lesson_sources(
                query, subject=state.get("context", {}).get("subject")
            )
        except Exception as error:
            logger.exception("تعذر جمع مصادر ملف الدرس: %s", error)
            sources = []

        sources = [source for source in sources if source.get("text")]
        if not sources:
            return _empty_result(
                state,
                "لم أجد مصادر مفهرسة عن هذا الدرس بعد؛ "
                "أضف المحتوى إلى قاعدة المعرفة ثم أعد المحاولة.",
                response_source="no_sources",
                retrieval_available=True,
            )

        topic = _pick_topic(sources, query, saved_topic)
        subject = state.get("context", {}).get("subject") or "غير محددة"
        spec = get_prompt("lesson_info", "teacher")
        selected, omitted = limit_sources(sources)
        synthesis_calls = 0

        try:
            rendered_size = sum(
                len(render_source(source, 1)) for source in selected
            )
            if rendered_size <= MAX_DIRECT_CHARS:
                prompt = spec.task.format(
                    topic=topic,
                    subject=subject,
                    sources=render_sources(selected),
                )
                response = await call_model(
                    prompt, spec.system, spec.temperature
                )
                synthesis_calls = 1
            else:
                batches = split_batches(selected)
                if len(batches) > MAX_BATCHES:
                    for batch in batches[MAX_BATCHES:]:
                        omitted.extend(batch)
                    batches = batches[:MAX_BATCHES]

                notes: list[str] = []
                offset = 1
                for batch in batches:
                    task = LESSON_INFO_EXTRACT_TASK.format(
                        topic=topic,
                        sources=render_sources(batch, start_index=offset),
                    )
                    notes.append(
                        await call_model(task, spec.system, spec.temperature)
                    )
                    offset += len(batch)

                compose = LESSON_INFO_COMPOSE_TASK.format(
                    topic=topic,
                    subject=subject,
                    notes="\n\n".join(notes),
                )
                response = await call_model(
                    compose, spec.system, spec.temperature
                )
                synthesis_calls = len(batches) + 1
        except Exception as error:
            logger.exception("تعذر توليف ملف الدرس: %s", error)
            response = _fallback_dossier(selected or sources)
            response_source = "fallback"
        else:
            response_source = "llm"

        response = _append_missing_references(response, sources)
        grades = sorted(
            {
                str(grade)
                for source in sources
                for grade in (source.get("grades") or [])
                if grade
            }
        )
        return {
            "response": response,
            "lesson_topic": topic,
            "metadata": append_node(
                state.get("metadata"),
                "lesson_info",
                intent=state.get("intent"),
                handled_by="lesson_info_node",
                response_source=response_source,
                lesson_info=True,
                source_count=len(sources),
                sources=[source.get("title") for source in sources],
                source_kinds=sorted(
                    {str(source.get("kind")) for source in sources}
                ),
                grades=grades,
                truncated=bool(omitted)
                or any(source.get("truncated") for source in sources),
                synthesis_calls=synthesis_calls,
            ),
        }

    return lesson_info_node
