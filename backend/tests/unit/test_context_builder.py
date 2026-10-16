"""اختبارات باني سياق المحادثة."""

from types import SimpleNamespace

from shared.context_builder import (
    build_classifier_view,
    build_generator_view,
    build_history_context,
)


def test_build_history_context_empty() -> None:
    """السياق الفارغ يعيد قائمة سوابق فارغة."""
    assert build_history_context([]) == {"history": []}


def test_build_history_context_keeps_last_limited_order() -> None:
    """الباني يحافظ على الترتيب ويأخذ آخر نافذة فقط."""
    rows = [
        SimpleNamespace(sender="user", content=f"رسالة {index}")
        for index in range(12)
    ]

    result = build_history_context(rows, limit=10)

    assert result == {
        "history": [
            {"sender": "user", "content": f"رسالة {index}"}
            for index in range(2, 12)
        ]
    }


def test_classifier_view_keeps_short_tail_only() -> None:
    """عرض المصنف: آخر 4 فقط لحل الضمائر بلا ضجيج."""
    rows = [
        SimpleNamespace(sender="user", content=f"رسالة {index}")
        for index in range(10)
    ]

    result = build_classifier_view(rows)

    assert [item["content"] for item in result["history"]] == [
        f"رسالة {index}" for index in range(6, 10)
    ]


def test_views_drop_empty_and_truncate_long() -> None:
    """العرضان يسقطان الفارغ ويقصان الطويل."""
    rows = [
        SimpleNamespace(sender="user", content="   "),
        SimpleNamespace(sender="user", content="س" * 500),
        SimpleNamespace(sender="assistant", content="رد قصير"),
    ]

    classifier = build_classifier_view(rows)
    generator = build_generator_view(rows)

    assert len(classifier["history"]) == 2
    assert len(classifier["history"][0]["content"]) == 120
    assert len(generator["history"][0]["content"]) == 300
    assert generator["history"][-1] == {
        "sender": "assistant",
        "content": "رد قصير",
    }


def test_generator_view_extracts_last_user_topics() -> None:
    """عرض المولد يستخرج آخر مواضيع المستخدم للتلخيص."""
    rows = [
        SimpleNamespace(sender="user", content="اشرح المفعول به"),
        SimpleNamespace(sender="assistant", content="شرح..."),
        SimpleNamespace(sender="user", content="وما إعراب الجملة؟"),
    ]

    result = build_generator_view(rows)

    assert result["last_topics"] == ["اشرح المفعول به", "وما إعراب الجملة؟"]
