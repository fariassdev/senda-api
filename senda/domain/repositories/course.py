import abc
from typing import Any

from senda.domain.dtos.course import (
    CourseDTO,
    CourseRecordDTO,
    CreateCourseDTO,
    UpdateCourseDTO,
)


class ICourseRepository(abc.ABC):
    """Course repository interface."""

    @abc.abstractmethod
    async def add(
        self, session: Any, author_id: int, create_item: CreateCourseDTO
    ) -> CourseRecordDTO: ...

    @abc.abstractmethod
    async def get_by_slug_or_none(
        self, session: Any, slug: str
    ) -> CourseRecordDTO | None: ...

    @abc.abstractmethod
    async def get_by_slug(self, session: Any, slug: str) -> CourseRecordDTO: ...

    @abc.abstractmethod
    async def get_by_id(
        self, session: Any, course_id: int
    ) -> CourseRecordDTO | None: ...

    @abc.abstractmethod
    async def delete_by_slug(self, session: Any, slug: str) -> None: ...

    @abc.abstractmethod
    async def update_by_slug(
        self, session: Any, slug: str, update_item: UpdateCourseDTO
    ) -> CourseRecordDTO: ...

    @abc.abstractmethod
    async def list_by_followings(
        self, session: Any, user_id: int, limit: int, offset: int
    ) -> list[CourseRecordDTO]: ...

    @abc.abstractmethod
    async def list_by_followings_v2(
        self, session: Any, user_id: int, limit: int, offset: int
    ) -> list[CourseDTO]: ...

    @abc.abstractmethod
    async def list_by_filters(
        self,
        session: Any,
        limit: int,
        offset: int,
        tag: str | None = None,
        author: str | None = None,
        favorited: str | None = None,
    ) -> list[CourseRecordDTO]: ...

    @abc.abstractmethod
    async def list_by_filters_v2(
        self,
        session: Any,
        user_id: int | None,
        limit: int,
        offset: int,
        tag: str | None = None,
        author: str | None = None,
        favorited: str | None = None,
    ) -> list[CourseDTO]: ...

    @abc.abstractmethod
    async def count_by_followings(self, session: Any, user_id: int) -> int: ...

    @abc.abstractmethod
    async def count_by_filters(
        self,
        session: Any,
        tag: str | None = None,
        author: str | None = None,
        favorited: str | None = None,
    ) -> int: ...
