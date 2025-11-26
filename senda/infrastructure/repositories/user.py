from collections.abc import Collection
from datetime import datetime

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.exceptions import UserNotFoundException
from senda.domain.dtos.user import CreateUserDTO, UpdateUserDTO, UserDTO
from senda.domain.mapper import IModelMapper
from senda.domain.repositories.user import IUserRepository
from senda.infrastructure.models import User
from senda.services.password import get_password_hash


class UserRepository(IUserRepository):
    """Repository for User model."""

    def __init__(self, user_mapper: IModelMapper[User, UserDTO]):
        self._user_mapper = user_mapper

    async def add(self, session: AsyncSession, create_item: CreateUserDTO) -> UserDTO:
        query = (
            insert(User)
            .values(
                username=create_item.username,
                email=create_item.email,
                password_hash=get_password_hash(create_item.password),
                image_url="https://api.realworld.io/images/smiley-cyrus.jpeg",
                bio=None,
                name=create_item.name,
                created_at=datetime.now(),
            )
            .returning(User)
        )
        result = await session.execute(query)
        return self._user_mapper.to_dto(result.scalar())

    async def get_by_email_or_none(
        self, session: AsyncSession, email: str
    ) -> UserDTO | None:
        query = select(User).where(User.email == email)
        if user := await session.scalar(query):
            return self._user_mapper.to_dto(user)

    async def get_by_email(self, session: AsyncSession, email: str) -> UserDTO:
        query = select(User).where(User.email == email)
        if not (user := await session.scalar(query)):
            raise UserNotFoundException()
        return self._user_mapper.to_dto(user)

    async def get_or_none(self, session: AsyncSession, user_id: int) -> UserDTO | None:
        query = select(User).where(User.id == user_id)
        if user := await session.scalar(query):
            return self._user_mapper.to_dto(user)

    async def get(self, session: AsyncSession, user_id: int) -> UserDTO:
        query = select(User).where(User.id == user_id)
        if not (user := await session.scalar(query)):
            raise UserNotFoundException()
        return self._user_mapper.to_dto(user)

    async def list_by_users(
        self, session: AsyncSession, user_ids: Collection[int]
    ) -> list[UserDTO]:
        query = select(User).where(User.id.in_(user_ids))
        users = await session.scalars(query)
        return [self._user_mapper.to_dto(user) for user in users]

    async def get_by_username_or_none(
        self, session: AsyncSession, username: str
    ) -> UserDTO | None:
        query = select(User).where(User.username == username)
        if user := await session.scalar(query):
            return self._user_mapper.to_dto(user)

    async def get_by_username(self, session: AsyncSession, username: str) -> UserDTO:
        query = select(User).where(User.username == username)
        if not (user := await session.scalar(query)):
            raise UserNotFoundException()
        return self._user_mapper.to_dto(user)

    async def update(
        self, session: AsyncSession, user_id: int, update_item: UpdateUserDTO
    ) -> UserDTO:
        query = (
            update(User)
            .where(User.id == user_id)
            .values(updated_at=datetime.now())
            .returning(User)
        )
        if update_item.username is not None:
            query = query.values(username=update_item.username)
        if update_item.email is not None:
            query = query.values(email=update_item.email)
        if update_item.password is not None:
            query = query.values(password_hash=get_password_hash(update_item.password))
        if update_item.bio is not None:
            query = query.values(bio=update_item.bio)
        if update_item.image_url is not None:
            query = query.values(image_url=update_item.image_url)
        if update_item.name is not None:
            query = query.values(name=update_item.name)

        result = await session.execute(query)
        return self._user_mapper.to_dto(result.scalar())
