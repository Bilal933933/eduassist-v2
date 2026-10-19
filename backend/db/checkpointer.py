"""إنشاء نقطة تفتيش لانغ غراف المدعومة بـ PostgreSQL."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from db.connection import open_database_pool


@asynccontextmanager
async def open_checkpointer(
    database_url: str,
) -> AsyncIterator[AsyncPostgresSaver]:
    """ربط نقطة تفتيش لانغ غراف بتجمع اتصالات قاعدة البيانات."""
    async with open_database_pool(database_url) as pool:
        yield AsyncPostgresSaver(pool)
