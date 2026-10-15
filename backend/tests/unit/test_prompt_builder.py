"""اختبارات باني الموجه المشترك."""

import json

import pytest

from shared.prompt_builder import build_prompt


def test_build_prompt_collects_all_model_inputs() -> None:
    """يجمع الباني الرسالة والسياق والمهمة والدور دون استدعاء النموذج."""
    prompt = build_prompt(
        message="اشرح الفاعل",
        context={"lesson": "النحو"},
        task="explain",
        role="teacher",
    )

    assert json.loads(prompt) == {
        "message": "اشرح الفاعل",
        "context": {"lesson": "النحو"},
        "task": "explain",
        "role": "teacher",
    }


def test_build_prompt_rejects_empty_message() -> None:
    """يرفض الباني إنشاء موجه بلا رسالة."""
    with pytest.raises(ValueError, match="دون رسالة"):
        build_prompt("", {}, "answer", "assistant")
