"""اختبارات فرض أمان الإعدادات في بيئة الإنتاج."""
import pytest
from pydantic import ValidationError

from config.settings import Settings

PRODUCTION = {
    "ENV": "production",
    "DATABASE_URL": "postgresql://app:s3cret@db.internal:5432/eduassist",
    "GEMINI_API_KEY": "key-123",
    "BACKEND_CORS_ORIGINS": "https://app.example.com",
}


def _settings(**overrides: str) -> Settings:
    """بناء إعدادات معزولة عن ملف .env المحلي."""
    return Settings(_env_file=None, **{**PRODUCTION, **overrides})  # type: ignore[arg-type]


def test_valid_production_settings_are_accepted() -> None:
    """إعدادات إنتاج كاملة تُقبل وتفعّل علم الإنتاج."""
    assert _settings().is_production is True


def test_development_defaults_are_accepted() -> None:
    """قيم التطوير الافتراضية مقبولة خارج الإنتاج."""
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.ENV == "development"
    assert settings.is_production is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"DATABASE_URL": "postgresql://eduassist:eduassist@db:5432/eduassist"},
        {"GEMINI_API_KEY": "   "},
        {"BACKEND_CORS_ORIGINS": "http://app.example.com"},
        {"BACKEND_CORS_ORIGINS": "https://app.example.com,http://localhost:3005"},
        {"BACKEND_CORS_ORIGINS": ""},
    ],
)
def test_unsafe_production_settings_fail_fast(overrides: dict[str, str]) -> None:
    """أي إعداد إنتاج غير آمن يمنع بدء التطبيق."""
    with pytest.raises(ValidationError):
        _settings(**overrides)


@pytest.mark.parametrize("value", ["prod", "Production", "staging"])
def test_unknown_env_value_is_rejected(value: str) -> None:
    """قيمة ENV غير معروفة ترفض البدء بدل تعطيل الحماية بصمت."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, ENV=value)  # type: ignore[arg-type]


def test_rate_limit_values_must_be_positive() -> None:
    """حدود المعدل الصفرية أو السالبة مرفوضة."""
    with pytest.raises(ValidationError):
        Settings(_env_file=None, AUTH_RATE_LIMIT_MAX=0)  # type: ignore[call-arg]
