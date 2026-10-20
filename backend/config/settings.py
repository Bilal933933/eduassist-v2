"""إعدادات التطبيق (تُقرأ من متغيرات البيئة)."""
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# بيانات اعتماد التطوير الافتراضية (مرفوضة في الإنتاج).
DEFAULT_DATABASE_URL = "postgresql://eduassist:eduassist@127.0.0.1:5432/eduassist"
DEV_DATABASE_CREDENTIALS = "eduassist:eduassist@"


class Settings(BaseSettings):
    """إعدادات الواجهة الخلفية."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── عام (قيمة غير معروفة مثل "prod" ترفض البدء بدل تعطيل الحماية بصمت) ───
    ENV: Literal["development", "test", "production"] = "development"

    # ─── الواجهة الخلفية ───
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 5002
    BACKEND_CORS_ORIGINS: str = "http://localhost:3005,http://127.0.0.1:3005"

    # ─── قاعدة البيانات ───
    DATABASE_URL: str = DEFAULT_DATABASE_URL

    # ─── المصادقة والجلسات ───
    AUTH_COOKIE_NAME: str = "eduassist_session"
    AUTH_SESSION_DAYS: int = 30

    # ─── تحديد المعدل (طلبات لكل نافذة بالثواني) ───
    AUTH_RATE_LIMIT_MAX: int = Field(default=10, gt=0)
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, gt=0)
    CHAT_RATE_LIMIT_MAX: int = Field(default=20, gt=0)
    CHAT_RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, gt=0)

    # ─── نموذج اللغة الكبير ───
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"

    # ─── وضع التصحيح ───
    # يتيح إخراج ميتا ديتا مصدر الرد (العقدة والنية ومسار التنفيذ) في الأحداث
    # وقاعدة البيانات؛ يبقى معطّلًا افتراضيًا حتى لا تتسرب أسماء العقد للعميل.
    DEBUG_METADATA: bool = False

    @property
    def is_production(self) -> bool:
        """هل يعمل التطبيق في بيئة الإنتاج."""
        return self.ENV == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        """تحويل نص المصادر المسموحة إلى قائمة."""
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_production_safety(self) -> Self:
        """فشل البدء عند ضعف إعدادات الإنتاج بدل العمل بصمت بقيم التطوير."""
        if not self.is_production:
            return self
        problems: list[str] = []
        if DEV_DATABASE_CREDENTIALS in self.DATABASE_URL:
            problems.append("DATABASE_URL يستخدم بيانات اعتماد التطوير")
        if not self.GEMINI_API_KEY.strip():
            problems.append("GEMINI_API_KEY فارغ")
        origins = self.cors_origins_list
        if not origins or any(not o.startswith("https://") for o in origins):
            problems.append("BACKEND_CORS_ORIGINS يجب أن تكون أصول https فقط")
        if problems:
            raise ValueError("إعدادات الإنتاج غير آمنة: " + "؛ ".join(problems))
        return self


settings = Settings()  # type: ignore[call-arg]
