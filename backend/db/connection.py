"""إدارة تجمع الاتصالات غير المتزامن بقاعدة PostgreSQL."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


@asynccontextmanager
async def open_database_pool(database_url: str) -> AsyncIterator[AsyncConnectionPool]:
    """فتح تجمع اتصالات وإغلاقه بعد انتهاء الاستخدام."""
    pool = AsyncConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=10,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=False,
    )
    await pool.open(wait=True)
    try:
        yield pool
    finally:
        await pool.close()
