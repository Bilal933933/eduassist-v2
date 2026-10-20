"""اختبارات محول جوجل جيمناي دون اتصال خارجي."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import adapters.llm.gemini as gemini_module
from adapters.llm.gemini import GeminiClient


def test_gemini_generates_with_system_prompt(monkeypatch) -> None:
    """يرسل المحول الرسالة وموجه النظام ويعيد النص فقط."""
    generate_content = AsyncMock(return_value=SimpleNamespace(text="رد جيمناي"))
    fake_client = Mock()
    fake_client.aio.models.generate_content = generate_content
    monkeypatch.setattr(gemini_module.genai, "Client", lambda api_key: fake_client)

    client = GeminiClient("test-key", "test-model")
    result = asyncio.run(client.generate("اشرح النحو", "موجه اختباري", 0.1))

    assert result == "رد جيمناي"
    call = generate_content.await_args.kwargs
    assert call["model"] == "test-model"
    assert call["contents"] == "اشرح النحو"
    assert call["config"].system_instruction == "موجه اختباري"
    # نماذج 3.x تدير العينات بنفسها فلا تُرسل temperature إطلاقًا.
    assert call["config"].temperature is None


def test_gemini_generates_enum_choice(monkeypatch) -> None:
    """يطلب المحول إخراج تعداد منظمًا للتصنيف."""
    generate_content = AsyncMock(return_value=SimpleNamespace(text="greeting"))
    fake_client = Mock()
    fake_client.aio.models.generate_content = generate_content
    monkeypatch.setattr(gemini_module.genai, "Client", lambda api_key: fake_client)

    client = GeminiClient("test-key", "test-model")
    result = asyncio.run(
        client.generate_enum("صنف الرسالة", ("greeting", "generation"))
    )

    assert result == "greeting"
    call = generate_content.await_args.kwargs
    assert call["config"].response_mime_type == "text/x.enum"
    assert {item.value for item in call["config"].response_schema} == {
        "greeting",
        "generation",
    }


def test_gemini_checks_api_key_only_when_model_is_called(monkeypatch) -> None:
    """يسمح بإنشاء المحول ثم يرفض الاتصال الفعلي دون مفتاح."""
    create_client = Mock()
    monkeypatch.setattr(gemini_module.genai, "Client", create_client)

    client = GeminiClient("   ", "test-model")

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        asyncio.run(client.generate("رسالة", "موجه", 0.1))

    create_client.assert_not_called()


def test_gemini_retries_transient_timeout_then_succeeds(monkeypatch) -> None:
    """يعيد المحول المحاولة عند مهلة عابرة وينجح دون انتظار حقيقي."""
    generate_content = AsyncMock(
        side_effect=[
            TimeoutError("t1"),
            TimeoutError("t2"),
            SimpleNamespace(text="رد بعد محاولتين"),
        ]
    )
    fake_client = Mock()
    fake_client.aio.models.generate_content = generate_content
    monkeypatch.setattr(gemini_module.genai, "Client", lambda api_key: fake_client)
    monkeypatch.setattr(gemini_module.asyncio, "sleep", AsyncMock())

    client = GeminiClient("test-key", "test-model")
    result = asyncio.run(client.generate("اشرح النحو", "موجه اختباري", 0.1))

    assert result == "رد بعد محاولتين"
    assert generate_content.await_count == 3


def test_gemini_gives_up_after_max_attempts(monkeypatch) -> None:
    """يستسلم المحول بعد ثلاث محاولات فاشلة ويمرر الخطأ."""
    generate_content = AsyncMock(side_effect=TimeoutError("down"))
    fake_client = Mock()
    fake_client.aio.models.generate_content = generate_content
    monkeypatch.setattr(gemini_module.genai, "Client", lambda api_key: fake_client)
    monkeypatch.setattr(gemini_module.asyncio, "sleep", AsyncMock())

    client = GeminiClient("test-key", "test-model")
    with pytest.raises(TimeoutError):
        asyncio.run(client.generate("رسالة", "موجه", 0.1))

    assert generate_content.await_count == 3


def test_gemini_does_not_retry_unexpected_errors(monkeypatch) -> None:
    """لا يعيد المحول المحاولة عند خطأ غير عابر (مثل البرمجة)."""
    generate_content = AsyncMock(side_effect=ValueError("bad args"))
    fake_client = Mock()
    fake_client.aio.models.generate_content = generate_content
    monkeypatch.setattr(gemini_module.genai, "Client", lambda api_key: fake_client)
    monkeypatch.setattr(gemini_module.asyncio, "sleep", AsyncMock())

    client = GeminiClient("test-key", "test-model")
    with pytest.raises(ValueError, match="bad args"):
        asyncio.run(client.generate("رسالة", "موجه", 0.1))

    assert generate_content.await_count == 1


def test_gemini_embeds_text_with_fixed_dimensions(monkeypatch) -> None:
    """يطلب المحول تضميناً بأبعاد مطابقة لعمود معرفة المنهج."""
    embed_content = AsyncMock(
        return_value=SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1] * 768)]
        )
    )
    fake_client = Mock()
    fake_client.aio.models.embed_content = embed_content
    monkeypatch.setattr(gemini_module.genai, "Client", lambda api_key: fake_client)

    client = GeminiClient("test-key", "test-model")
    result = asyncio.run(client.embed("كان وأخواتها"))

    assert len(result) == 768
    call = embed_content.await_args.kwargs
    assert call["model"] == "gemini-embedding-001"
    assert call["contents"] == "كان وأخواتها"
    assert call["config"].output_dimensionality == 768


def test_gemini_embed_rejects_wrong_dimensions(monkeypatch) -> None:
    """يرفض المحول متجهاً بأبعاد لا تطابق عمود المعرفة."""
    embed_content = AsyncMock(
        return_value=SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.1] * 16)]
        )
    )
    fake_client = Mock()
    fake_client.aio.models.embed_content = embed_content
    monkeypatch.setattr(gemini_module.genai, "Client", lambda api_key: fake_client)

    client = GeminiClient("test-key", "test-model")
    with pytest.raises(RuntimeError, match="أبعاد"):
        asyncio.run(client.embed("كان وأخواتها"))


def test_gemini_close_without_previous_connection() -> None:
    """لا يحتاج إغلاق المحول إلى إنشاء اتصال لم يُستخدم."""
    client = GeminiClient("", "test-model")

    asyncio.run(client.close())
