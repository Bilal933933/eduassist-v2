"""اختبارات منطق تجميع مصادر ملف الدرس."""
from __future__ import annotations

from retrieval.lesson_knowledge import (
    MAX_SOURCE_CHARS,
    build_curriculum_sources,
    coverage_missing,
    dedupe_sources,
    group_candidate_scopes,
    limit_sources,
    render_sources,
    split_batches,
    wikipedia_source,
)


def _chunk(
    chunk_id: int,
    content: str,
    *,
    source: str = "كتاب.md",
    chapter: str = "كان وأخواتها",
    grade: str = "أول إعدادي",
    subject: str = "نحو",
    score: float = 0.8,
) -> dict:
    return {
        "id": chunk_id,
        "content": content,
        "source": source,
        "chapter": chapter,
        "grade": grade,
        "subject": subject,
        "score": score,
    }


def test_group_candidate_scopes_collects_every_grade_once() -> None:
    """كل صف/مصدر يصبح نطاقًا مستقلًا، والأقوى أولًا."""
    scopes = group_candidate_scopes(
        [
            _chunk(1, "أ", grade="أول إعدادي", score=0.9),
            _chunk(2, "ب", grade="أول إعدادي", score=0.7),
            _chunk(3, "ج", grade="ثاني إعدادي", score=0.6),
            {**_chunk(4, "د"), "source": None},
        ]
    )

    assert [(s["grade"], s["score"]) for s in scopes] == [
        ("أول إعدادي", 0.9),
        ("ثاني إعدادي", 0.6),
    ]


def test_build_curriculum_sources_joins_all_chunks_and_dedupes() -> None:
    """النطاق يُجمع كاملًا، مع حذف التكرار ووسم الاقتطاع."""
    sources = build_curriculum_sources(
        [
            {
                "source": "كتاب.md",
                "chapter": "كان وأخواتها",
                "grade": "أول إعدادي",
                "subject": "نحو",
                "score": 0.9,
                "chunks": [
                    {"id": 2, "content": "الجزء الثاني"},
                    {"id": 1, "content": "الجزء الأول"},
                    {"id": 3, "content": "الجزء الأول"},
                ],
            }
        ],
        max_chars=MAX_SOURCE_CHARS,
    )

    assert len(sources) == 1
    assert sources[0]["kind"] == "curriculum"
    assert sources[0]["title"] == "كان وأخواتها"
    assert sources[0]["grades"] == ["أول إعدادي"]
    assert sources[0]["text"] == "الجزء الأول\n\nالجزء الثاني"
    assert sources[0]["truncated"] is False


def test_dedupe_sources_merges_duplicate_text_grades() -> None:
    """نفس النص في صفين يصبح مصدرًا واحدًا يحمل الصفين."""
    first = {
        "kind": "curriculum",
        "title": "كان وأخواتها",
        "text": "نص مشترك",
        "url": "",
        "subject": "نحو",
        "grades": ["أول إعدادي"],
        "chapter": "كان وأخواتها",
        "source": "أ.md",
        "score": 0.8,
        "truncated": False,
    }
    second = {
        **first,
        "grades": ["ثاني إعدادي"],
        "source": "ب.md",
        "score": 0.9,
    }

    merged = dedupe_sources([first, second])

    assert len(merged) == 1
    assert merged[0]["grades"] == ["أول إعدادي", "ثاني إعدادي"]
    assert merged[0]["score"] == 0.9


def test_wikipedia_source_marks_truncation() -> None:
    """صفحة ويكيبيديا تُحوَّل لمصدر موحد مع رابطها."""
    source = wikipedia_source(
        {
            "title": "كان وأخواتها",
            "url": "https://ar.wikipedia.org/wiki/كان_وأخواتها",
            "extract": "ن" * 400,
            "truncated": True,
        }
    )

    assert source["kind"] == "wikipedia"
    assert source["grades"] == []
    assert source["url"].startswith("https://")
    assert len(source["text"]) == 400
    assert source["truncated"] is True


def test_limit_sources_keeps_all_when_under_budget() -> None:
    """ضمن الميزانية لا يُحذف أي مصدر."""
    sources = [wikipedia_source({"title": f"م{i}", "extract": "ن" * 100}) for i in range(3)]

    selected, omitted = limit_sources(sources, max_total_chars=1000)

    assert selected == sources
    assert omitted == []


def test_limit_sources_drops_low_priority_overflow() -> None:
    """تجاوز الميزانية يحذف الأخير ويعلّمه كمصدر إضافي."""
    sources = [
        wikipedia_source({"title": "أ", "extract": "أ" * 600}),
        wikipedia_source({"title": "ب", "extract": "ب" * 600}),
    ]

    selected, omitted = limit_sources(sources, max_total_chars=700)

    assert [s["title"] for s in selected] == ["أ"]
    assert [s["title"] for s in omitted] == ["ب"]


def test_split_batches_respects_size() -> None:
    """تقسيم الدفعات يحافظ على الترتيب ولا يفرّغ أي مصدر."""
    sources = [
        wikipedia_source({"title": "أ", "extract": "أ" * 300}),
        wikipedia_source({"title": "ب", "extract": "ب" * 300}),
        wikipedia_source({"title": "ج", "extract": "ج" * 300}),
    ]

    batches = split_batches(sources, max_chars=400)

    assert len(batches) == 3
    assert [batch[0]["title"] for batch in batches] == ["أ", "ب", "ج"]


def test_render_sources_includes_refs_titles_urls_and_grades() -> None:
    """التنسيق يضع رقم المرجع والعنوان والرابط والصفوف."""
    sources = [
        {
            "kind": "curriculum",
            "title": "كان وأخواتها",
            "text": "نص الدرس",
            "url": "",
            "subject": "نحو",
            "grades": ["أول إعدادي", "ثاني إعدادي"],
            "chapter": "كان وأخواتها",
            "source": "كتاب.md",
            "score": 0.8,
            "truncated": True,
        }
    ]

    rendered = render_sources(sources)

    assert "[1]" in rendered
    assert "كان وأخواتها" in rendered
    assert "أول إعدادي، ثاني إعدادي" in rendered
    assert "نص الدرس" in rendered
    assert "مقتطع" in rendered


def test_coverage_missing_detects_uncited_sources() -> None:
    """المصدر يُعد مغطى إذا ظهر رقم مرجعه في الرد."""
    sources = [
        {"title": "الأول", "url": "https://a"},
        {"title": "الثاني", "url": "https://b"},
    ]

    missing = coverage_missing(sources, "اعتمدنا على [1] فقط")

    assert [s["title"] for s in missing] == ["الثاني"]
