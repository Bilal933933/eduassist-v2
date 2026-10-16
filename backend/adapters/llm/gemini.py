"""عميل جوجل جيمناي لتوليد الردود النصية."""

import asyncio
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

# ─── مهلة التوليد: أي تعليق يتحول لخطأ بدل تجميد الرسم ───
GENERATE_TIMEOUT_SECONDS = 60.0

# ─── إعادة المحاولة: الازدحام (503) والمهلة عابران عادة ───
RETRY_ATTEMPTS = 3
RETRY_BASE_DELAY_SECONDS = 1.0

T = TypeVar("T")


def _is_transient(error: Exception) -> bool:
    """المهلة وخطأ الخادم (5xx) عابران ويستحقان إعادة المحاولة."""
    return isinstance(error, TimeoutError | genai_errors.ServerError)


class GeminiClient:
    """استدعاء جيمناي وإرجاع النص الناتج فقط."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        """إنشاء عميل جيمناي عند أول اتصال فعلي فقط."""
        if self._client is not None:
            return self._client

        api_key = self._api_key.strip()
        if not api_key:
            raise RuntimeError(
                "متغير البيئة GEMINI_API_KEY مطلوب للاتصال بنموذج جيمناي."
            )

        self._client = genai.Client(api_key=api_key)
        return self._client

    async def _call_with_retry(
        self, operation: Callable[[], Awaitable[T]]
    ) -> T:
        """تنفيذ محاولة واحدة مع إعادة المحاولة عند خطأ عابر فقط."""
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                return await operation()
            except Exception as error:
                if attempt == RETRY_ATTEMPTS or not _is_transient(error):
                    raise
                delay = RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                await asyncio.sleep(delay)
        raise AssertionError("لا يمكن الوصول هنا: الحلقة تعيد أو ترفع دائمًا.")

    async def generate(
        self,
        message: str,
        system_prompt: str,
        temperature: float,
    ) -> str:
        """توليد رد عربي على رسالة المستخدم."""
        # نماذج 3.x تدير العينات بنفسها: تُقبل temperature للتوافق ولا تُرسل.
        _ = temperature

        async def attempt() -> str:
            response = await asyncio.wait_for(
                self._get_client().aio.models.generate_content(
                    model=self._model,
                    contents=message,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                    ),
                ),
                timeout=GENERATE_TIMEOUT_SECONDS,
            )
            if not response.text:
                raise RuntimeError("لم يُرجع جيمناي ردًا نصيًا.")
            return response.text

        return await self._call_with_retry(attempt)

    async def generate_enum(self, prompt: str, choices: tuple[str, ...]) -> str:
        """اختيار قيمة واحدة من قائمة محددة بإخراج منظم."""
        response_enum = Enum(
            "ResponseChoice",
            {choice.upper(): choice for choice in choices},
        )
        async def attempt() -> str:
            response = await asyncio.wait_for(
                self._get_client().aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="text/x.enum",
                        response_schema=response_enum,
                    ),
                ),
                timeout=GENERATE_TIMEOUT_SECONDS,
            )
            if not response.text:
                raise RuntimeError("لم يُرجع جيمناي قيمة تصنيف.")
            return response.text.strip()

        return await self._call_with_retry(attempt)

    async def close(self) -> None:
        """إغلاق اتصالات العميل غير المتزامن والمتزامن."""
        if self._client is None:
            return
        await self._client.aio.aclose()
        self._client.close()
