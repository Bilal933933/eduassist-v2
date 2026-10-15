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
    assert call["config"].temperature == 0.1


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


def test_gemini_close_without_previous_connection() -> None:
    """لا يحتاج إغلاق المحول إلى إنشاء اتصال لم يُستخدم."""
    client = GeminiClient("", "test-model")

    asyncio.run(client.close())
