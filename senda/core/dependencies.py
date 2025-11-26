from typing import Annotated, Awaitable, Callable

from fastapi import Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from senda.api.schemas.requests.course import CoursesFilters, CoursesPagination
from senda.core.container import container
from senda.core.enums import UserRole
from senda.core.exceptions import InsufficientPermissionsException
from senda.core.security import HTTPTokenHeader
from senda.domain.dtos.user import UserDTO
from senda.services.audio_generation import AudioGenerationService
from senda.services.auth import UserAuthService
from senda.services.auth_token import AuthTokenService
from senda.services.course import CourseService
from senda.services.lesson import LessonService
from senda.services.profile import ProfileService
from senda.services.script_generation import ScriptGenerationService
from senda.services.tag import TagService
from senda.services.user import UserService

token_security = HTTPTokenHeader(
    name="Authorization",
    scheme_name="JWT Token",
    description="Token Format: `Token xxxxxx.yyyyyyy.zzzzzz` or `Bearer xxxxxx.yyyyyyy.zzzzzz`",
    raise_error=True,
)
token_security_optional = HTTPTokenHeader(
    name="Authorization",
    scheme_name="JWT Token",
    description="Token Format: `Token xxxxxx.yyyyyyy.zzzzzz` or `Bearer xxxxxx.yyyyyyy.zzzzzz`",
    raise_error=False,
)

JWTToken = Annotated[str, Depends(token_security)]
JWTTokenOptional = Annotated[str, Depends(token_security_optional)]

DBSession = Annotated[AsyncSession, Depends(container.session)]

IAuthTokenService = Annotated[AuthTokenService, Depends(container.auth_token_service)]
IUserAuthService = Annotated[UserAuthService, Depends(container.user_auth_service)]
IUserService = Annotated[UserService, Depends(container.user_service)]
IProfileService = Annotated[ProfileService, Depends(container.profile_service)]
ITagService = Annotated[TagService, Depends(container.tag_service)]
ICourseService = Annotated[CourseService, Depends(container.course_service)]
ILessonService = Annotated[LessonService, Depends(container.lesson_service)]
IScriptGenerationService = Annotated[
    ScriptGenerationService, Depends(container.script_generation_service)
]
IAudioGenerationService = Annotated[
    AudioGenerationService, Depends(container.audio_generation_service)
]

DEFAULT_COURSES_LIMIT = 20
DEFAULT_COURSES_OFFSET = 0


def get_courses_pagination(
    limit: int = Query(DEFAULT_COURSES_LIMIT, ge=1),
    offset: int = Query(DEFAULT_COURSES_OFFSET, ge=0),
) -> CoursesPagination:
    limit = min(limit, DEFAULT_COURSES_LIMIT)
    return CoursesPagination(limit=limit, offset=offset)


def get_courses_filters(
    tag: str | None = None, author: str | None = None, favorited: str | None = None
) -> CoursesFilters:
    return CoursesFilters(tag=tag, author=author, favorited=favorited)


def require_auth(
    min_role: UserRole | None = None,
) -> Callable[..., Awaitable[UserDTO | None]]:
    """
    Unified authentication dependency factory with incremental permission checks.

    Args:
        min_role: Minimum required role. None allows unauthenticated access.
                  USER requires authenticated user, ADMIN requires admin role.

    Returns:
        FastAPI dependency that returns UserDTO | None (if min_role=None) or UserDTO.

    Raises:
        HTTPException: 403 if authentication required but token missing/invalid.
        InsufficientPermissionsException: If user role is below minimum required.

    Examples:
        # Public route with optional authentication
        current_user: Annotated[UserDTO | None, Depends(require_auth(min_role=None))]

        # Authenticated user required
        current_user: Annotated[UserDTO, Depends(require_auth(min_role=UserRole.USER))]

        # Admin only
        current_user: Annotated[UserDTO, Depends(require_auth(min_role=UserRole.ADMIN))]
    """

    async def _auth_dependency(
        token: Annotated[str, Depends(token_security_optional)],
        session: DBSession,
        auth_token_service: IAuthTokenService,
        user_service: IUserService,
    ) -> UserDTO | None:
        # Try to get user from token if present
        user: UserDTO | None = None
        if token:
            jwt_user = auth_token_service.parse_jwt_token(token=token)
            user = await user_service.get_user_by_id(
                session=session, user_id=jwt_user.user_id
            )

        # If no minimum role required, return user (or None for public access)
        if min_role is None:
            return user

        # Authentication required but no user found
        if user is None:
            raise HTTPException(status_code=403, detail="Authentication required.")

        # Check if user has sufficient permissions
        if user.role < min_role:
            raise InsufficientPermissionsException()

        return user

    return _auth_dependency


Pagination = Annotated[CoursesPagination, Depends(get_courses_pagination)]
QueryFilters = Annotated[CoursesFilters, Depends(get_courses_filters)]
OptionalUser = Annotated[UserDTO | None, Depends(require_auth(min_role=None))]
AuthenticatedUser = Annotated[UserDTO, Depends(require_auth(min_role=UserRole.USER))]
AdminUser = Annotated[UserDTO, Depends(require_auth(min_role=UserRole.ADMIN))]
