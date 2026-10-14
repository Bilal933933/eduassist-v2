"""إدارة الاتصال غير المتزامن بقاعدة PostgreSQL."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg.rows import dict_row


@asynccontextmanager
async def open_database_connection(database_url: str) -> AsyncIterator[AsyncConnection]:
    """فتح اتصال عام بقاعدة البيانات وإغلاقه بعد انتهاء الاستخدام."""
    connection = await AsyncConnection.connect(
        database_url,
        autocommit=True,
        prepare_threshold=0,
        row_factory=dict_row,
    )
    try:
        yield connection
    finally:
        await connection.close()
