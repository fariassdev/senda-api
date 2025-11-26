import abc
from typing import Any

from senda.domain.dtos.tag import TagDTO


class ICourseTagRepository(abc.ABC):
    """Course Tag repository interface."""

    @abc.abstractmethod
    async def add_many(
        self, session: Any, course_id: int, tags: list[str]
    ) -> list[TagDTO]: ...

    @abc.abstractmethod
    async def list(self, session: Any, course_id: int) -> list[TagDTO]: ...
