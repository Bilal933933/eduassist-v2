"""إعدادات التطبيق (Application Settings)."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """إعدادات القراءة من متغيرات البيئة (Environment Variables)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── عام (General) ───
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"

    # ─── قاعدة البيانات (Database) ───
    DATABASE_URL: str = "postgresql+asyncpg://eduassist:change_me@localhost:5432/eduassist"

    # ─── الواجهة الخلفية (Backend) ───
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000"

    # ─── البث (Realtime) ───
    REALTIME_ADAPTER: str = "sse"
    NESTJS_URL: str = ""
    INTERNAL_TOKEN: str = ""

    # ─── نموذج اللغة (LLM) ───
    LLM_PROVIDER: str = "google"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.0-flash"

    # ─── نموذج التضمين (Embedding) ───
    EMBEDDING_MODEL: str = "bge-m3"
    EMBEDDING_DIM: int = 1024

    @property
    def cors_origins_list(self) -> list[str]:
        """تحويل نص CORS إلى قائمة."""
        return [o.strip() for o in self.BACKEND_CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()  # type: ignore[call-arg]
