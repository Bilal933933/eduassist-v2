"""إنشاء نقطة تفتيش لانغ غراف المدعومة بـ PostgreSQL."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from db.connection import open_database_connection


@asynccontextmanager
async def open_checkpointer(
    database_url: str,
) -> AsyncIterator[AsyncPostgresSaver]:
    """ربط نقطة تفتيش لانغ غراف باتصال قاعدة البيانات."""
    async with open_database_connection(database_url) as connection:
        yield AsyncPostgresSaver(connection)
