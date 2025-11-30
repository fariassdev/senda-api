from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.enums import UserRole
from senda.domain.dtos.lesson import (
    CreateLessonDTO,
    LessonDTO,
    LessonsListDTO,
    ReorderLessonsDTO,
    UpdateLessonDTO,
)
from senda.domain.dtos.user import UserDTO
from senda.domain.repositories.course import ICourseRepository
from senda.domain.repositories.lesson import ILessonRepository
from senda.domain.services.lesson import ILessonService
from senda.domain.utils.script_serialization import LessonScript


class LessonService(ILessonService):
    def __init__(
        self, course_repo: ICourseRepository, lesson_repo: ILessonRepository
    ) -> None:
        self._course_repo = course_repo
        self._lesson_repo = lesson_repo

    async def create_course_lesson(
        self,
        session: AsyncSession,
        slug: str,
        lesson_to_create: CreateLessonDTO,
        current_user: UserDTO,
    ) -> LessonDTO:
        course = await self._course_repo.get_by_slug(session=session, slug=slug)

        lesson_record_dto = await self._lesson_repo.add(
            session=session,
            author_id=current_user.id,
            course_id=course.id,
            create_item=lesson_to_create,
        )

        return LessonDTO(
            id=lesson_record_dto.id,
            course_id=lesson_record_dto.course_id,
            lesson_number=lesson_record_dto.lesson_number,
            title=lesson_record_dto.title,
            core_practice=lesson_record_dto.core_practice,
            key_point=lesson_record_dto.key_point,
            tone=lesson_record_dto.tone,
            duration_minutes=lesson_record_dto.duration_minutes,
            status=lesson_record_dto.status,
            script=LessonScript.deserialize(lesson_record_dto.script),
            audio_url=lesson_record_dto.audio_url,
            script_generated_at=lesson_record_dto.script_generated_at,
            audio_generated_at=lesson_record_dto.audio_generated_at,
            created_at=lesson_record_dto.created_at,
            updated_at=lesson_record_dto.updated_at,
        )

    async def get_course_lessons(
        self, session: AsyncSession, slug: str, current_user: UserDTO | None = None
    ) -> LessonsListDTO:
        course = await self._course_repo.get_by_slug(session=session, slug=slug)
        lesson_records = await self._lesson_repo.list_by_course(
            session=session, course_id=course.id
        )

        lessons = [
            LessonDTO(
                id=lesson_record_dto.id,
                course_id=lesson_record_dto.course_id,
                lesson_number=lesson_record_dto.lesson_number,
                title=lesson_record_dto.title,
                core_practice=lesson_record_dto.core_practice,
                key_point=lesson_record_dto.key_point,
                tone=lesson_record_dto.tone,
                duration_minutes=lesson_record_dto.duration_minutes,
                status=lesson_record_dto.status,
                script=LessonScript.deserialize(lesson_record_dto.script),
                audio_url=lesson_record_dto.audio_url,
                script_generated_at=lesson_record_dto.script_generated_at,
                audio_generated_at=lesson_record_dto.audio_generated_at,
                created_at=lesson_record_dto.created_at,
                updated_at=lesson_record_dto.updated_at,
            )
            for lesson_record_dto in lesson_records
        ]

        lessons_count = await self._lesson_repo.count(
            session=session, course_id=course.id
        )
        return LessonsListDTO(lessons=lessons, lessons_count=lessons_count)

    async def delete_course_lesson(
        self, session: AsyncSession, slug: str, lesson_id: int, current_user: UserDTO
    ) -> None:
        await self._lesson_repo.delete(session=session, lesson_id=lesson_id)

    async def update_course_lesson(
        self,
        session: AsyncSession,
        slug: str,
        lesson_id: int,
        lesson_to_update: UpdateLessonDTO,
        current_user: UserDTO,
    ) -> LessonDTO:
        lesson_record_dto = await self._lesson_repo.update(
            session=session, lesson_id=lesson_id, update_item=lesson_to_update
        )

        return LessonDTO(
            id=lesson_record_dto.id,
            course_id=lesson_record_dto.course_id,
            lesson_number=lesson_record_dto.lesson_number,
            title=lesson_record_dto.title,
            core_practice=lesson_record_dto.core_practice,
            key_point=lesson_record_dto.key_point,
            tone=lesson_record_dto.tone,
            duration_minutes=lesson_record_dto.duration_minutes,
            status=lesson_record_dto.status,
            script=LessonScript.deserialize(lesson_record_dto.script),
            audio_url=lesson_record_dto.audio_url,
            script_generated_at=lesson_record_dto.script_generated_at,
            audio_generated_at=lesson_record_dto.audio_generated_at,
            created_at=lesson_record_dto.created_at,
            updated_at=lesson_record_dto.updated_at,
        )

    async def reorder_course_lessons(
        self,
        session: AsyncSession,
        slug: str,
        reorder_data: ReorderLessonsDTO,
        current_user: UserDTO,
    ) -> LessonsListDTO:
        course = await self._course_repo.get_by_slug(session=session, slug=slug)

        lesson_records = await self._lesson_repo.reorder(
            session=session, course_id=course.id, reorder_data=reorder_data
        )

        lessons = [
            LessonDTO(
                id=lesson_record_dto.id,
                course_id=lesson_record_dto.course_id,
                lesson_number=lesson_record_dto.lesson_number,
                title=lesson_record_dto.title,
                core_practice=lesson_record_dto.core_practice,
                key_point=lesson_record_dto.key_point,
                tone=lesson_record_dto.tone,
                duration_minutes=lesson_record_dto.duration_minutes,
                status=lesson_record_dto.status,
                script=LessonScript.deserialize(lesson_record_dto.script),
                audio_url=lesson_record_dto.audio_url,
                script_generated_at=lesson_record_dto.script_generated_at,
                audio_generated_at=lesson_record_dto.audio_generated_at,
                created_at=lesson_record_dto.created_at,
                updated_at=lesson_record_dto.updated_at,
            )
            for lesson_record_dto in lesson_records
        ]

        return LessonsListDTO(lessons=lessons, lessons_count=len(lessons))
