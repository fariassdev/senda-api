from typing import Annotated

from fastapi import Depends, Query
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
    description="Token Format: `Token xxxxxx.yyyyyyy.zzzzzz`",
    raise_error=True,
)
token_security_optional = HTTPTokenHeader(
    name="Authorization",
    scheme_name="JWT Token",
    description="Token Format: `Token xxxxxx.yyyyyyy.zzzzzz`",
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


async def get_current_user_or_none(
    token: JWTTokenOptional,
    session: DBSession,
    auth_token_service: IAuthTokenService,
    user_service: IUserService,
) -> UserDTO | None:
    if token:
        jwt_user = auth_token_service.parse_jwt_token(token=token)
        current_user_dto = await user_service.get_user_by_id(
            session=session, user_id=jwt_user.user_id
        )
        return current_user_dto


async def get_current_user(
    token: JWTToken,
    session: DBSession,
    auth_token_service: IAuthTokenService,
    user_service: IUserService,
) -> UserDTO:
    jwt_user = auth_token_service.parse_jwt_token(token=token)
    current_user_dto = await user_service.get_user_by_id(
        session=session, user_id=jwt_user.user_id
    )
    return current_user_dto


async def get_current_admin_user(
    current_user: Annotated[UserDTO, Depends(get_current_user)],
) -> UserDTO:
    """Require admin role for the current user."""
    if current_user.role != UserRole.ADMIN:
        raise InsufficientPermissionsException()
    return current_user


Pagination = Annotated[CoursesPagination, Depends(get_courses_pagination)]
QueryFilters = Annotated[CoursesFilters, Depends(get_courses_filters)]
CurrentOptionalUser = Annotated[UserDTO | None, Depends(get_current_user_or_none)]
CurrentUser = Annotated[UserDTO, Depends(get_current_user)]
CurrentAdminUser = Annotated[UserDTO, Depends(get_current_admin_user)]
