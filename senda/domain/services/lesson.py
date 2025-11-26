import abc
from typing import Any

from senda.domain.dtos.lesson import (
    CreateLessonDTO,
    LessonDTO,
    LessonsListDTO,
    UpdateLessonDTO,
)
from senda.domain.dtos.user import UserDTO


class ILessonService(abc.ABC):
    @abc.abstractmethod
    async def create_course_lesson(
        self,
        session: Any,
        slug: str,
        lesson_to_create: CreateLessonDTO,
        current_user: UserDTO,
    ) -> LessonDTO: ...

    @abc.abstractmethod
    async def get_course_lessons(
        self, session: Any, slug: str, current_user: UserDTO | None
    ) -> LessonsListDTO: ...

    @abc.abstractmethod
    async def delete_course_lesson(
        self, session: Any, slug: str, lesson_id: int, current_user: UserDTO
    ) -> None: ...

    @abc.abstractmethod
    async def update_course_lesson(
        self,
        session: Any,
        slug: str,
        lesson_id: int,
        lesson_to_update: UpdateLessonDTO,
        current_user: UserDTO,
    ) -> LessonDTO: ...
