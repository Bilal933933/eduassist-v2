"""عميل جوجل جيمناي لتوليد الردود النصية."""

from enum import Enum

from google import genai
from google.genai import types


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

    async def generate(
        self,
        message: str,
        system_prompt: str,
        temperature: float,
    ) -> str:
        """توليد رد عربي على رسالة المستخدم."""
        response = await self._get_client().aio.models.generate_content(
            model=self._model,
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
            ),
        )
        if not response.text:
            raise RuntimeError("لم يُرجع جيمناي ردًا نصيًا.")
        return response.text

    async def generate_enum(self, prompt: str, choices: tuple[str, ...]) -> str:
        """اختيار قيمة واحدة من قائمة محددة بإخراج منظم."""
        response_enum = Enum(
            "ResponseChoice",
            {choice.upper(): choice for choice in choices},
        )
        response = await self._get_client().aio.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="text/x.enum",
                response_schema=response_enum,
                temperature=0.0,
            ),
        )
        if not response.text:
            raise RuntimeError("لم يُرجع جيمناي قيمة تصنيف.")
        return response.text.strip()

    async def close(self) -> None:
        """إغلاق اتصالات العميل غير المتزامن والمتزامن."""
        if self._client is None:
            return
        await self._client.aio.aclose()
        self._client.close()
