"""فهرسة المعرفة (Indexer) — المرحلة 3: قراءة ملفات + تقطيع + تضمين + تخزين."""

import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from db.models.knowledge import KnowledgeChunk
from db.repositories.knowledge_repository import KnowledgeRepository
from retrieval.chunking import chunk_markdown, chunk_text


def _read_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """استخراج frontmatter YAML بسيط (--- ... ---) من Markdown."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not m:
        return {}, text
    fm_block, body = m.group(1), m.group(2)
    meta: dict[str, Any] = {}
    for line in fm_block.strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip("\"'")
    return meta, body


def _infer_metadata(file_path: Path, text_content: str) -> dict[str, Any]:
    """استنتاج metadata من المسار واسم الملف و frontmatter."""
    meta, body = _read_frontmatter(text_content)
    body = body.strip()
    # استنتاج من المسار
    parts = file_path.parts
    if "subject" not in meta:
        for part in parts:
            if part in ("نحو", "grammar", "syntax"):
                meta["subject"] = "نحو"
            elif part in ("صرف", "morphology"):
                meta["subject"] = "صرف"
    # استنتاج من اسم الملف
    stem = file_path.stem
    if "grade" not in meta:
        grade_match = re.search(r"(أول|ثاني|ثالث|رابع|خامس|سادس)\s*(إعدادي|متوسط|ابتدائي|ثانوي)", stem)
        if grade_match:
            meta["grade"] = grade_match.group(0)
    if "chapter" not in meta:
        meta.setdefault("chapter", stem)
    meta.setdefault("source", file_path.name)
    meta["_body"] = body
    return meta


def index_file(
    file_path: Path,
    repository: KnowledgeRepository,
    embed_fn: Callable[[str], list[float]],
    default_metadata: dict[str, Any] | None = None,
) -> int:
    """فهرسة ملف واحد. يعيد عدد القطع المخزنة."""
    text_content = file_path.read_text(encoding="utf-8")
    meta = _infer_metadata(file_path, text_content)
    body = meta.pop("_body", text_content)

    if default_metadata:
        for k, v in default_metadata.items():
            meta.setdefault(k, v)

    # اختيار طريقة التقطيع بناءً على الامتداد
    if file_path.suffix.lower() == ".md":
        chunks = chunk_markdown(body)
    else:
        chunks = [{"content": c, "heading": ""} for c in chunk_text(body)]

    if not chunks:
        return 0

    batch: list[dict[str, Any]] = []
    for ch in chunks:
        content = ch["content"].strip()
        if not content:
            continue
        vec = embed_fn(content)
        chunk_meta = {
            "content": content,
            "embedding": vec,
            "subject": meta.get("subject"),
            "grade": meta.get("grade"),
            "chapter": meta.get("chapter") or ch.get("heading"),
            "source": meta.get("source"),
            "metadata_": {
                k: v for k, v in meta.items() if k not in ("subject", "grade", "chapter", "source")
            },
        }
        batch.append(chunk_meta)

    if batch:
        # KnowledgeChunk constructor يتوقع metadata_ (وليس metadata)
        objs = []
        for b in batch:
            objs.append(
                KnowledgeChunk(
                    content=b["content"],
                    embedding=b["embedding"],
                    subject=b["subject"],
                    grade=b["grade"],
                    chapter=b["chapter"],
                    source=b["source"],
                    metadata_=b["metadata_"],
                )
            )
        repository._session.add_all(objs)  # noqa: SLF001
        # flush handled by caller or here
        import asyncio

        # We'll let the caller commit; but flush to get IDs
        # Since this is sync-ish wrapper, we handle async below
    return len(batch)


async def index_path(
    path: str | Path,
    repository: KnowledgeRepository,
    embed_fn: Callable[[str], list[float]],
    default_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """فهرسة ملف أو مجلد.

    Args:
        path: مسار ملف أو مجلد.
        repository: KnowledgeRepository محقون.
        embed_fn: دالة توليد embedding محقونة.
        default_metadata: metadata افتراضية.

    Returns:
        ملخص: {files: int, chunks: int, errors: list[str]}
    """
    path = Path(path)
    files: list[Path] = []
    if path.is_file():
        files = [path]
    elif path.is_dir():
        for ext in ("*.md", "*.txt"):
            files.extend(path.rglob(ext))
    else:
        return {"files": 0, "chunks": 0, "errors": [f"Path not found: {path}"]}

    total_chunks = 0
    errors: list[str] = []
    for fp in sorted(files):
        try:
            count = await _index_file_async(fp, repository, embed_fn, default_metadata)
            total_chunks += count
        except Exception as e:
            errors.append(f"{fp.name}: {e}")

    await repository._session.flush()  # noqa: SLF001
    return {"files": len(files), "chunks": total_chunks, "errors": errors}


async def _index_file_async(
    file_path: Path,
    repository: KnowledgeRepository,
    embed_fn: Callable[[str], list[float]],
    default_metadata: dict[str, Any] | None,
) -> int:
    """فهرسة ملف واحد (async)."""
    text_content = file_path.read_text(encoding="utf-8")
    meta = _infer_metadata(file_path, text_content)
    body = meta.pop("_body", text_content)

    if default_metadata:
        for k, v in default_metadata.items():
            meta.setdefault(k, v)

    if file_path.suffix.lower() == ".md":
        chunks = chunk_markdown(body)
    else:
        chunks = [{"content": c, "heading": ""} for c in chunk_text(body)]

    if not chunks:
        return 0

    batch: list[dict[str, Any]] = []
    for ch in chunks:
        content = ch["content"].strip()
        if not content:
            continue
        vec = embed_fn(content)
        batch.append(
            {
                "content": content,
                "embedding": vec,
                "subject": meta.get("subject"),
                "grade": meta.get("grade"),
                "chapter": meta.get("chapter") or ch.get("heading"),
                "source": meta.get("source"),
                "metadata_": {
                    k: v for k, v in meta.items() if k not in ("subject", "grade", "chapter", "source")
                },
            }
        )

    if batch:
        await repository.add_chunks_batch(batch)

    return len(batch)
