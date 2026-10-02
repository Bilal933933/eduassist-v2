"""مسار فحص الصحة (Health Check)."""
from fastapi import APIRouter

router = APIRouter(tags=["صحة"])


@router.get("/health")
async def health() -> dict:
    """فحص صحة الواجهة الخلفية."""
    return {"status": "ok", "service": "eduassist-backend"}
