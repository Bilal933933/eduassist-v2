"""مسارات بروفايل المعلم."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from api.schemas.common import SuccessResponse, ok
from api.schemas.profile import TeacherProfileRequest, TeacherProfileResponse
from db.models import TeacherProfile, User
from services.profile_service import get_profile, upsert_profile

router = APIRouter(prefix="/api/profile", tags=["بروفايل المعلم"])


def _to_profile_response(profile: TeacherProfile) -> dict:
    """تحويل صف البروفايل إلى حمولة عامة."""
    return TeacherProfileResponse(
        subject=profile.subject,
        class_name=profile.class_name,
        students_note=profile.students_note or "",
    ).model_dump(mode="json")


@router.get("", response_model=SuccessResponse[TeacherProfileResponse | None])
async def read_profile(
    session: AsyncSession = Depends(get_db),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> dict:
    """إرجاع بروفايل المعلم إن كان مضبوطًا، وإلا فارغ."""
    profile = await get_profile(session, user.id, user.role)
    if profile is None:
        return ok(None)
    return ok(_to_profile_response(profile))


@router.put("", response_model=SuccessResponse[TeacherProfileResponse])
async def update_profile(
    payload: TeacherProfileRequest,
    session: AsyncSession = Depends(get_db),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
) -> dict:
    """ضبط بروفايل المعلم أو تحديثه."""
    profile = await upsert_profile(
        session,
        user.id,
        user.role,
        payload.subject,
        payload.class_name,
        payload.students_note,
    )
    await session.commit()
    return ok(_to_profile_response(profile))
