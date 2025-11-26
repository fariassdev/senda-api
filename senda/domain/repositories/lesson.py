import abc
from typing import Any

from senda.domain.dtos.lesson import CreateLessonDTO, LessonRecordDTO, UpdateLessonDTO


class ILessonRepository(abc.ABC):
    """Lesson repository interface."""

    @abc.abstractmethod
    async def add(
        self, session: Any, author_id: int, course_id: int, create_item: CreateLessonDTO
    ) -> LessonRecordDTO: ...

    @abc.abstractmethod
    async def get_or_none(
        self, session: Any, lesson_id: int
    ) -> LessonRecordDTO | None: ...

    @abc.abstractmethod
    async def get(self, session: Any, lesson_id: int) -> LessonRecordDTO: ...

    @abc.abstractmethod
    async def list_by_course(
        self, session: Any, course_id: int
    ) -> list[LessonRecordDTO]: ...

    @abc.abstractmethod
    async def delete(self, session: Any, lesson_id: int) -> None: ...

    @abc.abstractmethod
    async def count(self, session: Any, course_id: int) -> int: ...

    @abc.abstractmethod
    async def update(
        self, session: Any, lesson_id: int, update_item: UpdateLessonDTO
    ) -> LessonRecordDTO: ...
