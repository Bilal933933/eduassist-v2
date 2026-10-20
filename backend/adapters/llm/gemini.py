"""عميل جوجل جيمناي لتوليد الردود النصية."""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import TypeVar

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

logger = logging.getLogger("eduassist.llm")

# ─── مهلة التوليد: أي تعليق يتحول لخطأ بدل تجميد الرسم ───
GENERATE_TIMEOUT_SECONDS = 20.0

# ─── إعادة المحاولة: المهلة عابرة، والازدحام يُحوَّل للبديل فورًا ───
RETRY_ATTEMPTS = 2
RETRY_BASE_DELAY_SECONDS = 1.0

# ─── قاطع الدائرة: بعد إخفاقين متتاليين يُتخطى الأساسي مدة قصيرة ───
PRIMARY_FAILURE_THRESHOLD = 2
PRIMARY_COOLDOWN_SECONDS = 60.0

# ─── التضمين: يجب أن يطابق أبعاد عمود knowledge_chunks (Vector(768)) ───
EMBEDDING_DIMENSIONS = 768

T = TypeVar("T")


def _is_transient(error: Exception) -> bool:
    """المهلة وخطأ الخادم (5xx) عابران ويستحقان إعادة المحاولة."""
    return isinstance(error, TimeoutError | genai_errors.ServerError)


def _is_timeout(error: Exception) -> bool:
    """المهلة وحدها تُعاد قبل تحويل الأساسي للبديل."""
    return isinstance(error, TimeoutError)


def _should_fallback(error: Exception) -> bool:
    """الازدحام (5xx) والحصة (429) والموديل المتقادم (404) تستحق البديل.

    المهلة ليست عطلًا في النموذج نفسه، فتُعاد على الأساسي بدل التحويل
    إلى بديل أبطأ يضاعف مدة الانتظار.
    """
    if isinstance(error, genai_errors.ServerError):
        return True
    if isinstance(error, genai_errors.ClientError):
        text = str(error)
        return (
            "NOT_FOUND" in text
            or "404" in text
            or "429" in text
            or "RESOURCE_EXHAUSTED" in text
        )
    return False


class GeminiClient:
    """استدعاء جيمناي وإرجاع النص الناتج فقط."""

    def __init__(
        self,
        api_key: str,
        model: str,
        fallback_model: str = "gemini-3.5-flash-lite",
        embedding_model: str = "gemini-embedding-001",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._fallback_model = fallback_model
        self._embedding_model = embedding_model
        self._client: genai.Client | None = None
        self._primary_failures = 0
        self._primary_skip_until = 0.0

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
        self,
        operation: Callable[[], Awaitable[T]],
        *,
        retry_server_errors: bool = True,
    ) -> T:
        """تنفيذ محاولة واحدة مع إعادة المحاولة عند خطأ عابر فقط."""
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                return await operation()
            except Exception as error:
                retryable = (
                    _is_transient(error)
                    if retry_server_errors
                    else _is_timeout(error)
                )
                if attempt == RETRY_ATTEMPTS or not retryable:
                    raise
                delay = RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1))
                await asyncio.sleep(delay)
        raise AssertionError("لا يمكن الوصول هنا: الحلقة تعيد أو ترفع دائمًا.")

    def _primary_allowed(self) -> bool:
        """هل يسمح القاطع بمحاولة النموذج الأساسي الآن."""
        return time.monotonic() >= self._primary_skip_until

    def _record_primary_failure(self) -> None:
        """رفع عدّاد إخفاق الأساسي وفتح القاطع عند بلوغ الحد."""
        self._primary_failures += 1
        if self._primary_failures >= PRIMARY_FAILURE_THRESHOLD:
            self._primary_skip_until = time.monotonic() + PRIMARY_COOLDOWN_SECONDS
            logger.warning(
                "تخطي النموذج الأساسي %s مدة %s ثانية بعد %s إخفاقات.",
                self._model,
                int(PRIMARY_COOLDOWN_SECONDS),
                self._primary_failures,
            )

    def _record_primary_success(self) -> None:
        """إغلاق القاطع بعد نجاح الأساسي."""
        self._primary_failures = 0
        self._primary_skip_until = 0.0

    async def _timed(self, model: str, operation: Callable[[], Awaitable[T]]) -> T:
        """تشغيل نداء نموذج مع تسجيل زمنه ونتيجته."""
        started = time.perf_counter()
        try:
            result = await operation()
        except Exception as error:
            logger.warning(
                "فشل نداء %s بعد %.1f ثانية: %s",
                model,
                time.perf_counter() - started,
                type(error).__name__,
            )
            raise
        logger.info(
            "نجح نداء %s في %.1f ثانية.", model, time.perf_counter() - started
        )
        return result

    async def _run_with_failover(
        self, attempt: Callable[[str], Awaitable[T]]
    ) -> T:
        """محاولة الأساسي ثم التحويل الفوري للبديل عند عطل يحتاج بديلًا."""
        if self._fallback_model == self._model:
            return await self._call_with_retry(
                lambda: self._timed(self._model, lambda: attempt(self._model)),
                retry_server_errors=False,
            )

        if self._primary_allowed():
            try:
                result = await self._call_with_retry(
                    lambda: self._timed(self._model, lambda: attempt(self._model)),
                    retry_server_errors=False,
                )
            except Exception as error:
                if not _should_fallback(error):
                    raise
                self._record_primary_failure()
            else:
                self._record_primary_success()
                return result

        return await self._call_with_retry(
            lambda: self._timed(
                self._fallback_model, lambda: attempt(self._fallback_model)
            )
        )

    async def generate(
        self,
        message: str,
        system_prompt: str,
        temperature: float,
    ) -> str:
        """توليد رد عربي على رسالة المستخدم."""
        # نماذج 3.x تدير العينات بنفسها: تُقبل temperature للتوافق ولا تُرسل.
        _ = temperature

        async def attempt(model: str) -> str:
            response = await asyncio.wait_for(
                self._get_client().aio.models.generate_content(
                    model=model,
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

        return await self._run_with_failover(attempt)

    async def generate_enum(self, prompt: str, choices: tuple[str, ...]) -> str:
        """اختيار قيمة واحدة من قائمة محددة بإخراج منظم."""
        response_enum = Enum(
            "ResponseChoice",
            {choice.upper(): choice for choice in choices},
        )
        async def attempt(model: str) -> str:
            response = await asyncio.wait_for(
                self._get_client().aio.models.generate_content(
                    model=model,
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

        return await self._run_with_failover(attempt)

    async def embed(self, text: str) -> list[float]:
        """توليد متجه تضمين بأبعاد مطابقة لعمود knowledge_chunks."""
        async def attempt(model: str) -> list[float]:
            response = await asyncio.wait_for(
                self._get_client().aio.models.embed_content(
                    model=model,
                    contents=text,
                    config=types.EmbedContentConfig(
                        output_dimensionality=EMBEDDING_DIMENSIONS,
                    ),
                ),
                timeout=GENERATE_TIMEOUT_SECONDS,
            )
            values = list(response.embeddings[0].values) if response.embeddings else []
            if not values:
                raise RuntimeError("لم يُرجع جيمناي متجه تضمين.")
            if len(values) != EMBEDDING_DIMENSIONS:
                raise RuntimeError(
                    f"أبعاد التضمين {len(values)} لا تطابق عمود "
                    f"knowledge_chunks ({EMBEDDING_DIMENSIONS})."
                )
            return values

        return await self._call_with_retry(lambda: attempt(self._embedding_model))

    async def close(self) -> None:
        """إغلاق اتصالات العميل غير المتزامن والمتزامن."""
        if self._client is None:
            return
        await self._client.aio.aclose()
        self._client.close()
