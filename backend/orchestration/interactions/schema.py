"""عقود تمثيل رسالة المستخدم وبطاقة استكمال البيانات."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from orchestration.state.agent import Intent

InteractionStatus = Literal["open", "answered", "dismissed", "expired"]


class InterpretedMessage(BaseModel):
    """الرسالة الأصلية مع النية والخصائص المستخرجة."""

    model_config = ConfigDict(extra="ignore")

    text: str
    intent: Intent
    properties: dict[str, Any] = Field(default_factory=dict)


class Interpretation(BaseModel):
    """غلاف إخراج المصنف المنظم."""

    model_config = ConfigDict(extra="ignore")

    message: InterpretedMessage


class InteractionOption(BaseModel):
    """خيار مغلق داخل سؤال."""

    label: str
    value: str


class InteractionQuestion(BaseModel):
    """سؤال واحد في بطاقة استكمال البيانات."""

    slot: str
    prompt: str
    options: list[InteractionOption] = Field(default_factory=list)
    allow_custom: bool = True
    required: bool = True


class Interaction(BaseModel):
    """بطاقة أسئلة مرتبطة برسالة المساعد نفسها."""

    status: InteractionStatus = "open"
    intent: Intent
    properties: dict[str, Any] = Field(default_factory=dict)
    questions: list[InteractionQuestion]
    answers: dict[str, str] | None = None
