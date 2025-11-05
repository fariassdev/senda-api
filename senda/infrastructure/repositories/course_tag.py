from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from senda.domain.dtos.tag import TagDTO
from senda.domain.mapper import IModelMapper
from senda.domain.repositories.course_tag import ICourseTagRepository
from senda.infrastructure.models import CourseTag, Tag


class CourseTagRepository(ICourseTagRepository):
    """Repository for Course Tag model."""

    def __init__(self, tag_mapper: IModelMapper[Tag, TagDTO]):
        self._tag_mapper = tag_mapper

    async def add_many(
        self, session: AsyncSession, course_id: int, tags: list[str]
    ) -> list[TagDTO]:
        insert_query = (
            insert(Tag)
            .on_conflict_do_nothing()
            .values([{"tag": tag, "created_at": datetime.now()} for tag in tags])
        )
        await session.execute(insert_query)

        select_query = select(Tag).where(Tag.tag.in_(tags))
        tags = await session.scalars(select_query)
        tags = [self._tag_mapper.to_dto(tag) for tag in tags]

        link_query = (
            insert(CourseTag)
            .on_conflict_do_nothing()
            .values(
                [
                    {
                        "course_id": course_id,
                        "tag_id": tag.id,
                        "created_at": datetime.now(),
                    }
                    for tag in tags
                ]
            )
        )
        await session.execute(link_query)

        return tags

    async def list(self, session: AsyncSession, course_id: int) -> list[TagDTO]:
        query = (
            select(Tag, CourseTag)
            .where((CourseTag.course_id == course_id) & (CourseTag.tag_id == Tag.id))
            .order_by(Tag.created_at.desc())
        )
        tags = await session.scalars(query)
        return [self._tag_mapper.to_dto(tag) for tag in tags]
