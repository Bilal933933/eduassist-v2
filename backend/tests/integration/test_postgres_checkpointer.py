"""اختبار تكامل نقطة التفتيش مع PostgreSQL المحلية."""
import asyncio
import os
import selectors
import sys

import pytest

from config.settings import settings
from db.checkpointer import open_checkpointer
from graph import build_graph, checkpoint_config


@pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_TESTS") != "1",
    reason="يتطلب قاعدة PostgreSQL محلية مهيأة.",
)
def test_postgres_checkpointer_persists_graph_state() -> None:
    """يحفظ الرسم حالته في PostgreSQL ويسترجعها للمحادثة نفسها."""

    async def scenario() -> None:
        async def fake_generate(
            message: str, system_prompt: str, temperature: float
        ) -> str:
            _ = system_prompt, temperature
            return message

        async def fake_classify(prompt: str, choices: tuple[str, ...]) -> str:
            _ = prompt, choices
            return "generation"

        config = checkpoint_config("integration-user", "integration-thread")
        async with open_checkpointer(settings.DATABASE_URL) as checkpointer:
            persistent_graph = build_graph(
                checkpointer,
                call_model=fake_generate,
                classify_intent=fake_classify,
            )
            await persistent_graph.ainvoke(
                {"messages": ["الأولى"], "user_id": "integration-user"},
                config,
            )
            result = await persistent_graph.ainvoke(
                {"messages": ["الثانية"], "user_id": "integration-user"},
                config,
            )
            assert result["messages"][-2:] == ["الأولى", "الثانية"]
            await checkpointer.adelete_thread(
                config["configurable"]["thread_id"],
            )

    if sys.platform == "win32":
        with asyncio.Runner(
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        ) as runner:
            runner.run(scenario())
    else:
        asyncio.run(scenario())
