"""تقطيع النص (Chunking) لفهرسة المعرفة — المرحلة 3."""

import re


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[str]:
    """تقطيع نص عادي بنافذة منزلقة (sliding window).

    Args:
        text: النص الكامل.
        chunk_size: حد أقصى لأحرف كل قطعة.
        overlap: عدد الأحرف المتداخلة بين قطع متتالية.

    Returns:
        قائمة قطع نصية.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
        if start < 0:
            start = 0

    return chunks


def _split_on_headings(text: str) -> list[tuple[str, str]]:
    """تقسيم Markdown على عناوين # / ## / ###.

    Returns:
        list of (heading, body) tuples.
    """
    lines = text.split("\n")
    sections: list[tuple[str, str]] = []
    current_heading = ""
    current_body: list[str] = []

    for line in lines:
        m = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
        if m:
            if current_body:
                sections.append((current_heading, "\n".join(current_body).strip()))
            current_heading = m.group(2).strip()
            current_body = []
        else:
            current_body.append(line)

    if current_body or current_heading:
        sections.append((current_heading, "\n".join(current_body).strip()))

    # إذا لم تُعثر على أي عنوان، treat whole text as one section
    if not sections or all(not h for h, _ in sections):
        return [("", text.strip())]

    return sections


def chunk_markdown(
    text: str,
    chunk_size: int = 800,
    overlap: int = 100,
) -> list[dict]:
    """تقطيع Markdown: تقسيم أولي على العناوين، ثم تقطيع إضافي إن needed.

    Returns:
        list of dicts: {content, heading}
    """
    text = text.strip()
    if not text:
        return []

    sections = _split_on_headings(text)
    result: list[dict] = []

    for heading, body in sections:
        if not body:
            continue
        # جمع العنوان + المتن
        full = f"{heading}\n\n{body}".strip() if heading else body
        if len(full) <= chunk_size:
            result.append({"content": full, "heading": heading})
        else:
            # تقطيع إضافي
            sub_chunks = chunk_text(full, chunk_size, overlap)
            for sc in sub_chunks:
                result.append({"content": sc, "heading": heading})

    return result
