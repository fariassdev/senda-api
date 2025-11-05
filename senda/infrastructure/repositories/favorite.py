from datetime import datetime

from sqlalchemy import delete, exists, insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count

from senda.domain.repositories.favorite import IFavoriteRepository
from senda.infrastructure.models import Favorite


class FavoriteRepository(IFavoriteRepository):
    """Repository for Follower model."""

    async def exists(
        self, session: AsyncSession, author_id: int, course_id: int
    ) -> bool:
        query = (
            exists()
            .where(Favorite.user_id == author_id, Favorite.course_id == course_id)
            .select()
        )
        result = await session.execute(query)
        return result.scalar()

    async def count(self, session: AsyncSession, course_id: int) -> int:
        query = select(count()).where(Favorite.course_id == course_id)
        result = await session.execute(query)
        return result.scalar()

    async def create(self, session: AsyncSession, course_id: int, user_id: int) -> None:
        query = insert(Favorite).values(
            user_id=user_id, course_id=course_id, created_at=datetime.now()
        )
        await session.execute(query)

    async def delete(self, session: AsyncSession, course_id: int, user_id: int) -> None:
        query = delete(Favorite).where(
            Favorite.user_id == user_id, Favorite.course_id == course_id
        )
        await session.execute(query)
