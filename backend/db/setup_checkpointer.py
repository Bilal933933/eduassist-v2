"""إنشاء جداول نقاط تفتيش لانغ غراف لمرة واحدة."""
import asyncio
import selectors
import sys

from config.settings import settings
from db.checkpointer import open_checkpointer


async def setup() -> None:
    """إنشاء جداول الحافظ وترحيلاته الرسمية."""
    async with open_checkpointer(settings.DATABASE_URL) as checkpointer:
        await checkpointer.setup()


if __name__ == "__main__":
    if sys.platform == "win32":
        with asyncio.Runner(
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        ) as runner:
            runner.run(setup())
    else:
        asyncio.run(setup())
