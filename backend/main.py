"""نقطة دخول فاستAPI (FastAPI)."""
import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.llm import GeminiClient
from services.errors.handlers import register_error_handlers
from api.routes.auth import router as auth_router
from api.routes.chat import router as chat_router
from config.settings import settings
from db.checkpointer import open_checkpointer
from db.session import open_session_factory
from graph import build_graph
from realtime.routes import router as events_router


if sys.platform == "win32":
    # يحتاج اتصال PostgreSQL غير المتزامن إلى حلقة أحداث متوافقة على ويندوز.
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """ربط عمر التطبيق باتصالات PostgreSQL اللازمة."""
    gemini = GeminiClient(
        settings.GEMINI_API_KEY,
        settings.GEMINI_MODEL,
        settings.GEMINI_FALLBACK_MODEL,
    )
    async with (
        open_checkpointer(settings.DATABASE_URL) as checkpointer,
        open_session_factory(settings.DATABASE_URL) as session_factory,
    ):
        try:
            app.state.graph = build_graph(
                checkpointer,
                call_model=gemini.generate,
                classify_intent=gemini.generate_enum,
            )
            app.state.session_factory = session_factory
            yield
        finally:
            await gemini.close()


app = FastAPI(title="EduAssist V2 API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_error_handlers(app)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(events_router)
