from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from senda.core.exceptions import IncorrectLoginInputException, UserNotFoundException
from senda.domain.dtos.user import (
    CreatedUserDTO,
    CreateUserDTO,
    LoggedInUserDTO,
    LoginUserDTO,
)
from senda.domain.services.auth import IUserAuthService
from senda.domain.services.auth_token import IAuthTokenService
from senda.domain.services.user import IUserService
from senda.services.password import verify_password

logger = get_logger()


class UserAuthService(IUserAuthService):
    """Service to handle users auth logic."""

    def __init__(
        self, user_service: IUserService, auth_token_service: IAuthTokenService
    ):
        self._user_service = user_service
        self._auth_token_service = auth_token_service

    async def sign_up_user(
        self, session: AsyncSession, user_to_create: CreateUserDTO
    ) -> CreatedUserDTO:
        user = await self._user_service.create_user(
            session=session, user_to_create=user_to_create
        )
        jwt_token = self._auth_token_service.generate_jwt_token(user=user)
        return CreatedUserDTO(
            id=user.id,
            email=user.email,
            username=user.username,
            name=user.name,
            bio=user.bio,
            image=user.image_url,
            token=jwt_token,
        )

    async def sign_in_user(
        self, session: AsyncSession, user_to_login: LoginUserDTO
    ) -> LoggedInUserDTO:
        try:
            user = await self._user_service.get_user_by_email(
                session=session, email=user_to_login.email
            )
        except UserNotFoundException:
            logger.error("User not found", email=user_to_login.email)
            raise IncorrectLoginInputException() from None

        if not verify_password(
            plain_password=user_to_login.password, hashed_password=user.password_hash
        ):
            logger.error("Incorrect password", user_id=user_to_login.email)
            raise IncorrectLoginInputException()

        jwt_token = self._auth_token_service.generate_jwt_token(user=user)
        return LoggedInUserDTO(
            email=user.email,
            username=user.username,
            name=user.name,
            bio=user.bio,
            image=user.image_url,
            token=jwt_token,
        )
