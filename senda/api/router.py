from fastapi import APIRouter

from senda.api.routes import (
    audio_jobs,
    authentication,
    course,
    health_check,
    lesson,
    profile,
    tag,
    users,
    voices,
)

router = APIRouter()

router.include_router(
    router=health_check.router, tags=["Health Check"], prefix="/health-check"
)
router.include_router(
    router=authentication.router, tags=["Authentication"], prefix="/users"
)
router.include_router(router=users.router, tags=["User"], prefix="/user")
router.include_router(router=profile.router, tags=["Profiles"], prefix="/profiles")
router.include_router(router=tag.router, tags=["Tags"], prefix="/tags")
router.include_router(router=course.router, tags=["Courses"], prefix="/courses")
router.include_router(router=lesson.router, tags=["Lessons"], prefix="/courses")
router.include_router(router=audio_jobs.router, tags=["Audio Jobs"], prefix="/jobs")
router.include_router(router=voices.router, tags=["Voices"], prefix="")
