"""تجميع مصادر ملف الدرس وتنسيقها بحدود واضحة.

العقدة تحتاج «كل معلومات الدرس» لا أقرب المقاطع فقط، ثم تحتاج تحويل ذلك
إلى نص منظم لا يتجاوز سياق النموذج. هذا الملف منطق نقي بلا قاعدة بيانات
أو شبكة، ليسهل اختباره واستخدامه من الخدمة والعقدة.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

MAX_INTERNAL_GROUPS = 12
MAX_CHUNKS_PER_GROUP = 40
MAX_SOURCE_CHARS = 6000
MAX_TOTAL_SOURCE_CHARS = 30000
MAX_DIRECT_CHARS = 18000
MAX_BATCH_CHARS = 12000
MAX_BATCHES = 4
MAX_WIKIPEDIA_PAGES = 6
WIKIPEDIA_PAGES_WITH_INTERNAL = 2


def normalize_text(text: str) -> str:
    """توحيد الأسطر وتقليص الفراغات الزائدة قبل التجميع."""
    value = str(text or "").replace("\r\n", "\n").strip()
    return re.sub(r"\n{3,}", "\n\n", value)


def _fingerprint(text: str) -> str:
    """بصمة نصية لمقارنة التكرار بين المصادر والصفوف."""
    normalized = re.sub(r"\s+", " ", normalize_text(text).casefold())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def group_candidate_scopes(
    candidates: list[dict[str, Any]],
    *,
    max_groups: int = MAX_INTERNAL_GROUPS,
) -> list[dict[str, Any]]:
    """تحويل المرشحين إلى نطاقات (مصدر، فصل، صف) فريدة.

    النطاق هو ما سنوسّعه لاحقًا لجلب كل مقاطع الدرس، لا المرشحين فقط.
    """
    scopes: dict[tuple[str, str | None, str | None], dict[str, Any]] = {}
    for candidate in candidates:
        source = str(candidate.get("source") or "").strip()
        if not source:
            continue
        chapter = str(candidate.get("chapter") or "").strip() or None
        grade = str(candidate.get("grade") or "").strip() or None
        key = (source, chapter, grade)
        score = float(candidate.get("score") or 0.0)
        current = scopes.get(key)
        if current is None:
            scopes[key] = {
                "source": source,
                "chapter": chapter,
                "grade": grade,
                "subject": candidate.get("subject"),
                "score": score,
            }
        elif score > current["score"]:
            current["score"] = score
            current["subject"] = candidate.get("subject") or current["subject"]

    ordered = sorted(
        scopes.values(), key=lambda scope: scope["score"], reverse=True
    )
    return ordered[:max_groups]


def build_curriculum_sources(
    groups: list[dict[str, Any]],
    *,
    max_chars: int = MAX_SOURCE_CHARS,
) -> list[dict[str, Any]]:
    """جمع مقاطع كل نطاق في مصدر واحد مرتب، مع حذف التكرار.

    ``groups`` عناصرها تحمل ``source`` و``chapter`` و``grade`` و``chunks``.
    """
    sources: list[dict[str, Any]] = []
    for group in groups:
        chunks = list(group.get("chunks") or [])
        chunks.sort(key=lambda chunk: int(chunk.get("id") or 0))
        seen: set[str] = set()
        parts: list[str] = []
        for chunk in chunks[:MAX_CHUNKS_PER_GROUP]:
            text = normalize_text(chunk.get("content", ""))
            if not text:
                continue
            fingerprint = _fingerprint(text)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            parts.append(text)

        if not parts:
            continue

        full_text = "\n\n".join(parts)
        chapter = group.get("chapter")
        source = group.get("source")
        title = str(chapter or source or "مصدر منهجي").strip()
        grade = group.get("grade")
        sources.append(
            {
                "kind": "curriculum",
                "title": title,
                "text": full_text[:max_chars],
                "url": "",
                "subject": group.get("subject"),
                "grades": [str(grade)] if grade else [],
                "chapter": chapter,
                "source": source,
                "score": float(group.get("score") or 0.0),
                "truncated": len(full_text) > max_chars,
            }
        )
    return sources


def wikipedia_source(page: dict[str, Any]) -> dict[str, Any]:
    """تحويل صفحة ويكيبيديا إلى المصدر الموحد نفسه."""
    text = normalize_text(page.get("extract", ""))
    return {
        "kind": "wikipedia",
        "title": str(page.get("title") or "ويكيبيديا").strip(),
        "text": text[:MAX_SOURCE_CHARS],
        "url": str(page.get("url") or ""),
        "subject": None,
        "grades": [],
        "chapter": None,
        "source": None,
        "score": 0.0,
        "truncated": bool(page.get("truncated")) or len(text) > MAX_SOURCE_CHARS,
    }


def dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """حذف المصادر المكررة ودمج صفوفها، مع إبقاء الترتيب الأول."""
    unique: list[dict[str, Any]] = []
    by_fingerprint: dict[str, dict[str, Any]] = {}
    for source in sources:
        text = normalize_text(source.get("text", ""))
        if not text:
            continue
        fingerprint = _fingerprint(text)
        existing = by_fingerprint.get(fingerprint)
        if existing is not None:
            for grade in source.get("grades") or []:
                if grade not in existing["grades"]:
                    existing["grades"].append(grade)
            existing["truncated"] = existing["truncated"] or bool(
                source.get("truncated")
            )
            existing["score"] = max(
                float(existing.get("score") or 0.0),
                float(source.get("score") or 0.0),
            )
            continue

        item = {
            **source,
            "text": text,
            "grades": list(dict.fromkeys(source.get("grades") or [])),
        }
        by_fingerprint[fingerprint] = item
        unique.append(item)
    return unique


def limit_sources(
    sources: list[dict[str, Any]],
    *,
    max_total_chars: int = MAX_TOTAL_SOURCE_CHARS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """اقتصاص المصادر عند الميزانية الكلية، وإرجاع الفائض للتوثيق."""
    selected: list[dict[str, Any]] = []
    omitted: list[dict[str, Any]] = []
    total = 0
    for source in sources:
        length = len(source.get("text") or "")
        if selected and total + length > max_total_chars:
            omitted.append(source)
            continue
        selected.append(source)
        total += length
    return selected, omitted


def render_source(
    source: dict[str, Any],
    index: int,
    *,
    max_chars: int = MAX_SOURCE_CHARS,
) -> str:
    """تنسيق مصدر واحد برقم مرجع وبيانات وسم."""
    kind = "منهج داخلي" if source.get("kind") == "curriculum" else "ويكيبيديا"
    grades = "، ".join(source.get("grades") or []) or "غير محدد"
    text = str(source.get("text") or "")[:max_chars]
    lines = [
        f"[{index}] {source.get('title')}",
        f"النوع: {kind}",
        f"الصفوف: {grades}",
    ]
    if source.get("url"):
        lines.append(f"الرابط: {source['url']}")
    lines.extend(["النص:", text])
    if source.get("truncated") or len(str(source.get("text") or "")) > max_chars:
        lines.append("[النص مقتطع عند حد العرض]")
    return "\n".join(lines)


def render_sources(
    sources: list[dict[str, Any]],
    *,
    start_index: int = 1,
    max_chars: int = MAX_SOURCE_CHARS,
) -> str:
    """تنسيق مجموعة مصادر بمراجع متسلسلة تبدأ من ``start_index``."""
    blocks = [
        render_source(source, index, max_chars=max_chars)
        for index, source in enumerate(sources, start=start_index)
    ]
    return "\n\n".join(blocks)


def split_batches(
    sources: list[dict[str, Any]],
    *,
    max_chars: int = MAX_BATCH_CHARS,
) -> list[list[dict[str, Any]]]:
    """تقسيم المصادر إلى دفعات بحسب طول النص المنسق."""
    batches: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_size = 0
    for source in sources:
        block_size = len(render_source(source, 1))
        if current and current_size + block_size > max_chars:
            batches.append(current)
            current = []
            current_size = 0
        current.append(source)
        current_size += block_size
    if current:
        batches.append(current)
    return batches


def coverage_missing(
    sources: list[dict[str, Any]], response: str
) -> list[dict[str, Any]]:
    """المصادر التي لم يظهر رقم مرجعها في الرد النهائي.

    الاعتماد على الرقم لا العنوان يمنع اعتبار مصدرين يحملان العنوان نفسه
    مغطيين بمجرد ورود العنوان مرة واحدة.
    """
    missing: list[dict[str, Any]] = []
    for index, source in enumerate(sources, start=1):
        if f"[{index}]" in response:
            continue
        missing.append(source)
    return missing
