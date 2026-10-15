"""اختبارات تجزئة كلمات المرور."""
from security.passwords import hash_password, verify_password


def test_hash_then_verify_roundtrip() -> None:
    """التجزئة ثم التحقق بنفس الكلمة ينجح."""
    stored = hash_password("كلمة-مرور-قوية-123")
    assert verify_password("كلمة-مرور-قوية-123", stored) is True


def test_wrong_password_fails_verification() -> None:
    """كلمة خاطئة لا تجتاز التحقق."""
    stored = hash_password("الصحيحة-123")
    assert verify_password("الخاطئة-456", stored) is False


def test_two_hashes_of_same_password_differ() -> None:
    """الملح العشوائي يجعل تجزئتين لنفس الكلمة مختلفتين."""
    assert hash_password("نفس-الكلمة") != hash_password("نفس-الكلمة")


def test_malformed_stored_value_fails_safely() -> None:
    """قيمة مخزنة تالفة تُرفض دون استثناء."""
    assert verify_password("أي-شيء", "قيمة-تالفة") is False
