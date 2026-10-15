"""اختبارات رموز الجلسات."""
from security.session_tokens import generate_token, hash_token


def test_generated_tokens_are_unique() -> None:
    """كل رمز مولد مختلف عن الآخر."""
    assert generate_token() != generate_token()


def test_hash_is_deterministic_and_hides_raw() -> None:
    """نفس الخام يعطي نفس التجزئة، والتجزئة لا تكشف الخام."""
    raw = generate_token()
    assert hash_token(raw) == hash_token(raw)
    assert raw not in hash_token(raw)
