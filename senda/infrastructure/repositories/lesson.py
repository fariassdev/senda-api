from datetime import datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count

from senda.core.exceptions import LessonNotFoundException
from senda.domain.dtos.lesson import CreateLessonDTO, LessonRecordDTO, UpdateLessonDTO
from senda.domain.dtos.script_generation import ScriptPartDTO
from senda.domain.mapper import IModelMapper
from senda.domain.repositories.lesson import ILessonRepository
from senda.domain.utils.script_serialization import LessonScript
from senda.infrastructure.models import Lesson


class LessonRepository(ILessonRepository):
    def __init__(self, lesson_mapper: IModelMapper[Lesson, LessonRecordDTO]):
        self._lesson_mapper = lesson_mapper

    async def add(
        self,
        session: AsyncSession,
        author_id: int,
        course_id: int,
        create_item: CreateLessonDTO,
    ) -> LessonRecordDTO:
        query = (
            insert(Lesson)
            .values(
                course_id=course_id,
                lesson_number=create_item.lesson_number,
                title=create_item.title,
                core_practice=create_item.core_practice,
                key_point=create_item.key_point,
                tone=create_item.tone,
                duration_minutes=create_item.duration_minutes,
                status="PENDING",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            .returning(Lesson)
        )
        result = await session.execute(query)
        return self._lesson_mapper.to_dto(result.scalar())

    async def get_or_none(
        self, session: AsyncSession, lesson_id: int
    ) -> LessonRecordDTO | None:
        query = select(Lesson).where(Lesson.id == lesson_id)
        if lesson := await session.scalar(query):
            return self._lesson_mapper.to_dto(lesson)

    async def get(self, session: AsyncSession, lesson_id: int) -> LessonRecordDTO:
        query = select(Lesson).where(Lesson.id == lesson_id)
        if not (lesson := await session.scalar(query)):
            raise LessonNotFoundException()
        return self._lesson_mapper.to_dto(lesson)

    async def list_by_course(
        self, session: AsyncSession, course_id: int
    ) -> list[LessonRecordDTO]:
        query = (
            select(Lesson)
            .where(Lesson.course_id == course_id)
            .order_by(Lesson.lesson_number)
        )
        lessons = await session.scalars(query)
        return [self._lesson_mapper.to_dto(lesson) for lesson in lessons]

    async def delete(self, session: AsyncSession, lesson_id: int) -> None:
        query = delete(Lesson).where(Lesson.id == lesson_id)
        await session.execute(query)

    async def count(self, session: AsyncSession, course_id: int) -> int:
        query = select(count(Lesson.id)).where(Lesson.course_id == course_id)
        result = await session.execute(query)
        return result.scalar()

    async def update(
        self, session: AsyncSession, lesson_id: int, update_item: UpdateLessonDTO
    ) -> LessonRecordDTO:
        query = (
            update(Lesson)
            .where(Lesson.id == lesson_id)
            .values(updated_at=datetime.now())
            .returning(Lesson)
        )

        if update_item.title is not None:
            query = query.values(title=update_item.title)
        if update_item.core_practice is not None:
            query = query.values(core_practice=update_item.core_practice)
        if update_item.key_point is not None:
            query = query.values(key_point=update_item.key_point)
        if update_item.tone is not None:
            query = query.values(tone=update_item.tone)
        if update_item.duration_minutes is not None:
            query = query.values(duration_minutes=update_item.duration_minutes)
        if update_item.status is not None:
            query = query.values(status=update_item.status.value)
        if update_item.script is not None:
            # Use domain layer serialization
            query = query.values(script=LessonScript.serialize(update_item.script))
        if update_item.audio_url is not None:
            query = query.values(audio_url=update_item.audio_url)
        if update_item.script_generated_at is not None:
            query = query.values(script_generated_at=update_item.script_generated_at)

        lesson = await session.scalar(query)
        return self._lesson_mapper.to_dto(lesson)
