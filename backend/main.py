"""نقطة الدخول (Entry Point) للواجهة الخلفية."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """إدارة دورة حياة التطبيق."""
    # بدء التشغيل
    yield
    # الإغلاق


app = FastAPI(
    title="EduAssist V2 API",
    version="0.1.0",
    lifespan=lifespan,
)

# إعداد CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# المسارات
app.include_router(health.router)
