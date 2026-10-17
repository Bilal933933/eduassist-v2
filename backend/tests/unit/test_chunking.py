"""اختبارات وحدة للتقطيع (Chunking)."""

from retrieval.chunking import chunk_markdown, chunk_text


def test_chunk_text_short() -> None:
    """نص قصير → قطعة واحدة."""
    text = "قاعدة نحويّة قصيرة."
    result = chunk_text(text, chunk_size=800)
    assert result == [text]


def test_chunk_text_empty() -> None:
    """نص فارغ → قائمة فارغة."""
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_long() -> None:
    """نص طويل → عدة قطع."""
    text = "أ" * 2000
    result = chunk_text(text, chunk_size=800, overlap=100)
    assert len(result) >= 2
    # كل قطعة ≤ 800
    assert all(len(c) <= 800 for c in result)


def test_chunk_text_overlap() -> None:
    """القطع متداخلة (overlap)."""
    text = "أ" * 1000
    result = chunk_text(text, chunk_size=500, overlap=50)
    assert len(result) >= 2
    # التداخل: نهاية قطعة 1 ≈ بداية قطعة 2 - overlap
    assert result[0][-50:] == result[1][:50]


def test_chunk_markdown_headings() -> None:
    """تقسيم Markdown على عناوين."""
    md = """# الباب الأول

محتوى الباب الأول.

## 1.1 الفاعل

الفاعل مرفوع.

## 1.2 المفعول

المفعول به منصوب.
"""
    result = chunk_markdown(md, chunk_size=800)
    assert len(result) >= 2
    assert any("الفاعل" in r["content"] for r in result)
    assert any(r["heading"] for r in result)


def test_chunk_markdown_no_headings() -> None:
    """Markdown بدون عناوين → قطعة واحدة."""
    md = "نص بدون عناوين."
    result = chunk_markdown(md, chunk_size=800)
    assert len(result) == 1
    assert result[0]["content"] == md


def test_chunk_markdown_long_section() -> None:
    """قسم طويل → تقطيع إضافي."""
    md = "# عنوان\n\n" + "أ" * 2000
    result = chunk_markdown(md, chunk_size=800, overlap=100)
    assert len(result) >= 2
    assert all(len(r["content"]) <= 800 for r in result)
