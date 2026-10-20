"""اختبارات استخراج كائن JSON من ردود النماذج."""
from __future__ import annotations

from shared.json_parser import extract_json_object


def test_extract_plain_json_object() -> None:
    """يخرج الكائن من رد JSON مباشر."""
    parsed = extract_json_object('{"score": 0.9, "section": null}')
    assert parsed == {"score": 0.9, "section": None}


def test_extract_json_object_wrapped_in_markdown_fence() -> None:
    """يخرج الكائن من رد ملفوف بأسوار الماركداون."""
    parsed = extract_json_object('```json\n{"score": 0.95, "section": null}\n```')
    assert parsed == {"score": 0.95, "section": None}


def test_extract_json_object_with_text_around_it() -> None:
    """يخرج الكائن من رد يحوي شرحاً قبله."""
    parsed = extract_json_object(
        'هذا تقييمي:\n```json\n{"score": 0.4, "section": "lesson_flow"}\n```\nشكراً'
    )
    assert parsed == {"score": 0.4, "section": "lesson_flow"}


def test_extract_json_object_ignores_braces_inside_strings() -> None:
    """لا ينخدع بالأقواس الموجودة داخل النصوص."""
    parsed = extract_json_object('{"section": "القسم {كذا}", "score": 0.3}')
    assert parsed == {"section": "القسم {كذا}", "score": 0.3}


def test_extract_json_object_returns_none_for_plain_text() -> None:
    """يعيد None حين لا يوجد JSON في الرد."""
    assert extract_json_object("هذا ليس JSON") is None


def test_extract_json_object_returns_none_for_truncated_json() -> None:
    """يعيد None حين يكون الكائن غير مكتمل."""
    assert extract_json_object('{"score": 0.9, "section":') is None


def test_extract_json_object_returns_none_for_non_object_json() -> None:
    """يعيد None حين يكون JSON المصدَّق قائمة لا كائناً."""
    assert extract_json_object("[1, 2, 3]") is None


def test_extract_json_object_returns_none_for_empty_text() -> None:
    """يعيد None للرد الفارغ."""
    assert extract_json_object("") is None
