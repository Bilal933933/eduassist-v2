"""تجزئة كلمات المرور والتحقق منها بأرغون2 (Argon2)."""
from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError


_password_hash = PasswordHash.recommended()

# تجزئة ثابتة تُحسب مرة واحدة لمعادلة زمن الدخول عند غياب الحساب.
_DUMMY_HASH = _password_hash.hash("eduassist-timing-equalization")


def hash_password(plain: str) -> str:
    """تحويل كلمة خام إلى تجزئة أرغون2 للتخزين."""
    return _password_hash.hash(plain)


def verify_password(plain: str, stored: str) -> bool:
    """التحقق من كلمة خام مقابل تجزئة مخزنة دون تسريب السبب."""
    try:
        return _password_hash.verify(plain, stored)
    except (PwdlibError, ValueError, TypeError, AttributeError):
        return False


def verify_and_update_password(plain: str, stored: str) -> tuple[bool, str | None]:
    """التحقق وإرجاع تجزئة أحدث عند تغير إعدادات الحماية."""
    try:
        return _password_hash.verify_and_update(plain, stored)
    except (PwdlibError, ValueError, TypeError, AttributeError):
        return False, None


def burn_password_verification(plain: str) -> None:
    """إنفاق زمن تحقق أرغون2 كاملًا لإخفاء الفرق الزمني بين الحساب الغائب والموجود."""
    verify_password(plain, _DUMMY_HASH)
