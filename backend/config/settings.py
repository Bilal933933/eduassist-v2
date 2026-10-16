"""إعدادات التطبيق (تُقرأ من متغيرات البيئة)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """إعدادات الواجهة الخلفية."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── عام ───
    ENV: str = "development"

    # ─── الواجهة الخلفية ───
    BACKEND_HOST: str = "127.0.0.1"
    BACKEND_PORT: int = 5002
    BACKEND_CORS_ORIGINS: str = "http://localhost:3005,http://127.0.0.1:3005"

    # ─── قاعدة البيانات ───
    DATABASE_URL: str = "postgresql://eduassist:eduassist@127.0.0.1:5432/eduassist"

    # ─── المصادقة والجلسات ───
    AUTH_COOKIE_NAME: str = "eduassist_session"
    AUTH_SESSION_DAYS: int = 30

    # ─── نموذج اللغة الكبير ───
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.5-flash-lite"

    @property
    def cors_origins_list(self) -> list[str]:
        """تحويل نص المصادر المسموحة إلى قائمة."""
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()  # type: ignore[call-arg]
