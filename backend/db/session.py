"""إدارة جلسات مخطط الكائنات العلائقية لقاعدة البيانات."""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


SessionFactory = async_sessionmaker[AsyncSession]


def sqlalchemy_database_url(database_url: str) -> str:
    """تحويل رابط PostgreSQL إلى رابط مشغل psycopg غير المتزامن."""
    return database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )


@asynccontextmanager
async def open_session_factory(
    database_url: str,
) -> AsyncIterator[SessionFactory]:
    """إنشاء مصنع جلسات مشترك وإغلاق محركه مع التطبيق."""
    engine = create_async_engine(sqlalchemy_database_url(database_url))
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
