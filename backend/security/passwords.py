"""تجزئة كلمات المرور والتحقق منها بأرغون2 (Argon2)."""
from pwdlib import PasswordHash
from pwdlib.exceptions import PwdlibError


_password_hash = PasswordHash.recommended()


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
