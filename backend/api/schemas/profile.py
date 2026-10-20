"""نماذج بروفايل المعلم."""
from pydantic import BaseModel, Field, field_validator


class TeacherProfileRequest(BaseModel):
    """بيانات بروفايل المعلم التي تُغذّي تحضير الدرس."""

    subject: str = Field(min_length=1, max_length=100)
    class_name: str = Field(min_length=1, max_length=100)
    students_note: str = Field(default="", max_length=1000)

    @field_validator("subject", "class_name")
    @classmethod
    def normalize_required(cls, value: str) -> str:
        """تجريد الفراغات ورفض القيم الفارغة فعليًا."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("الحقل يجب ألا يكون فارغًا.")
        return normalized

    @field_validator("students_note")
    @classmethod
    def normalize_note(cls, value: str) -> str:
        """تجريد فراغات ملاحظة الطلاب."""
        return value.strip()


class TeacherProfileResponse(BaseModel):
    """بيانات بروفايل المعلم المعروضة للواجهة."""

    subject: str
    class_name: str
    students_note: str
