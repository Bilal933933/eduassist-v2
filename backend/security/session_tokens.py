"""توليد رموز الجلسات وتجزئتها (الخام لا يُخزَّن أبدًا)."""
import hashlib
import secrets


def generate_token() -> str:
    """توليد رمز عشوائي آمن يُرسل للمتصفح مرة واحدة."""
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    """تحويل الرمز الخام إلى تجزئة sha256 للتخزين والمقارنة."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
