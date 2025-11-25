from collections.abc import Collection

from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.enums import UserRole
from senda.core.exceptions import (
    EmailAlreadyTakenException,
    UserNameAlreadyTakenException,
)
from senda.domain.dtos.user import CreateUserDTO, UpdatedUserDTO, UpdateUserDTO, UserDTO
from senda.domain.repositories.user import IUserRepository
from senda.domain.services.user import IUserService


class UserService(IUserService):
    """Service to handle user get & update logic."""

    def __init__(self, user_repo: IUserRepository) -> None:
        self._user_repo = user_repo

    async def create_user(
        self, session: AsyncSession, user_to_create: CreateUserDTO
    ) -> UserDTO:
        if await self._user_repo.get_by_email_or_none(
            session=session, email=user_to_create.email
        ):
            raise EmailAlreadyTakenException()

        if await self._user_repo.get_by_username_or_none(
            session=session, username=user_to_create.username
        ):
            raise UserNameAlreadyTakenException()

        return await self._user_repo.add(session=session, create_item=user_to_create)

    async def get_user_by_id(self, session: AsyncSession, user_id: int) -> UserDTO:
        return await self._user_repo.get(session=session, user_id=user_id)

    async def get_user_by_email(self, session: AsyncSession, email: str) -> UserDTO:
        return await self._user_repo.get_by_email(session=session, email=email)

    async def get_user_by_username(
        self, session: AsyncSession, username: str
    ) -> UserDTO:
        return await self._user_repo.get_by_username(session=session, username=username)

    async def get_users_by_ids(
        self, session: AsyncSession, user_ids: Collection[int]
    ) -> list[UserDTO]:
        return await self._user_repo.list_by_users(session=session, user_ids=user_ids)

    async def update_user(
        self,
        session: AsyncSession,
        current_user: UserDTO,
        user_to_update: UpdateUserDTO,
    ) -> UpdatedUserDTO:
        if user_to_update.username and user_to_update.username != current_user.username:
            if await self._user_repo.get_by_username_or_none(
                session=session, username=user_to_update.username
            ):
                raise UserNameAlreadyTakenException()

        if user_to_update.email and user_to_update.email != current_user.email:
            if await self._user_repo.get_by_email_or_none(
                session=session, email=user_to_update.email
            ):
                raise EmailAlreadyTakenException()

        updated_user = await self._user_repo.update(
            session=session, user_id=current_user.id, update_item=user_to_update
        )
        return UpdatedUserDTO(
            id=updated_user.id,
            email=updated_user.email,
            username=updated_user.username,
            name=updated_user.name,
            bio=updated_user.bio,
            image=updated_user.image_url,
        )

    async def create_admin_user(
        self, session: AsyncSession, user_to_create: CreateUserDTO
    ) -> UserDTO:
        """Create a new admin user. Only callable by existing admin users."""
        if await self._user_repo.get_by_email_or_none(
            session=session, email=user_to_create.email
        ):
            raise EmailAlreadyTakenException()

        if await self._user_repo.get_by_username_or_none(
            session=session, username=user_to_create.username
        ):
            raise UserNameAlreadyTakenException()

        # Override role to ADMIN
        admin_user_dto = CreateUserDTO(
            username=user_to_create.username,
            email=user_to_create.email,
            password=user_to_create.password,
            name=user_to_create.name,
            role=UserRole.ADMIN,
        )

        return await self._user_repo.add(session=session, create_item=admin_user_dto)

    async def promote_user_to_admin(
        self, session: AsyncSession, user_id: int
    ) -> UserDTO:
        """Promote an existing user to admin role."""
        return await self._user_repo.update_user_role(
            session=session, user_id=user_id, role=UserRole.ADMIN
        )
