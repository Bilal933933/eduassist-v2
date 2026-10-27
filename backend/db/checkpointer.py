"""إنشاء نقطة تفتيش لانغ غراف المدعومة بـ PostgreSQL."""
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from db.connection import open_database_pool

logger = logging.getLogger("eduassist.checkpointer")


@asynccontextmanager
async def open_checkpointer(
    database_url: str,
) -> AsyncIterator[AsyncPostgresSaver]:
    """ربط نقطة تفتيش لانغ غراف بتجمع اتصالات قاعدة البيانات."""
    async with open_database_pool(database_url) as pool:
        yield AsyncPostgresSaver(pool)


async def delete_thread_checkpoints(
    checkpointer: object | None,
    thread_id: str,
) -> None:
    """حذف نقاط الرسم الخاصة بخيط المحادثة المحذوفة (أفضل جهد).

    الحذف في القاعدة ينجح حتى لو فشل تنظيف اللقطات، فالفشل هنا لا يُفشل الطلب.
    """
    if not isinstance(checkpointer, AsyncPostgresSaver):
        return
    try:
        await checkpointer.adelete_thread(thread_id)
    except Exception as error:
        logger.warning("تعذر حذف لقطات المحادثة %s: %s", thread_id, error)


async def prune_thread_checkpoints(
    checkpointer: object | None,
    thread_id: str,
) -> None:
    """حذف اللقطات القديمة للمحادثة مع الإبقاء على آخر لقطة لكل نطاق.

    كل خطوة في الرسم تكتب لقطة كاملة من الحالة، فتتراكم اللقطات مع طول
    المحادثة. التنظيف يحدث بعد كل دور فيبقى آخر حالة للرسم وتُمحى البقية.
    """
    if not isinstance(checkpointer, AsyncPostgresSaver):
        return
    try:
        await checkpointer.aprune([thread_id], strategy="keep_latest")
    except Exception as error:
        logger.warning("تعذر تنظيف لقطات المحادثة %s: %s", thread_id, error)
