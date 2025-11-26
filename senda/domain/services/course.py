import abc
from typing import Any

from senda.domain.dtos.course import (
    CourseDTO,
    CoursesFeedDTO,
    CreateCourseDTO,
    UpdateCourseDTO,
)
from senda.domain.dtos.course_generation import (
    CourseGenerationRequestDTO,
    CourseStructureDTO,
)
from senda.domain.dtos.lesson import LessonDTO
from senda.domain.dtos.user import UserDTO


class ICourseGenerationProvider(abc.ABC):
    """Abstract interface for AI-powered course structure generation."""

    @abc.abstractmethod
    async def generate_course_structure(
        self, request: CourseGenerationRequestDTO
    ) -> CourseStructureDTO:
        """
        Generates a complete course structure based on the provided prompt.

        Returns:
            CourseStructureDTO with title, description, lessons, etc.

        Raises:
            CourseGenerationException: If generation fails
            InvalidPromptException: If prompt violates content policy
        """
        pass


class ICourseService(abc.ABC):
    @abc.abstractmethod
    async def create_new_course(
        self, session: Any, author_id: int, course_to_create: CreateCourseDTO
    ) -> CourseDTO: ...

    @abc.abstractmethod
    async def create_course_from_prompt(
        self, session: Any, request: CourseGenerationRequestDTO
    ) -> tuple[CourseDTO, list[LessonDTO]]:
        """
        Generates and creates a complete course with lessons using AI.

        Returns:
            Tuple of (CourseDTO, List[LessonDTO]) with complete course and all lessons

        Raises:
            CourseGenerationException: If generation or creation fails
        """
        ...

    @abc.abstractmethod
    async def get_course_by_slug(
        self, session: Any, slug: str, current_user: UserDTO | None
    ) -> CourseDTO: ...

    @abc.abstractmethod
    async def delete_course_by_slug(
        self, session: Any, slug: str, current_user: UserDTO
    ) -> None: ...

    @abc.abstractmethod
    async def get_courses_feed(
        self, session: Any, current_user: UserDTO, limit: int, offset: int
    ) -> CoursesFeedDTO: ...

    @abc.abstractmethod
    async def get_courses_feed_v2(
        self, session: Any, current_user: UserDTO, limit: int, offset: int
    ) -> CoursesFeedDTO: ...

    @abc.abstractmethod
    async def get_courses_by_filters(
        self,
        session: Any,
        current_user: UserDTO | None,
        limit: int,
        offset: int,
        tag: str | None = None,
        author: str | None = None,
        favorited: str | None = None,
    ) -> CoursesFeedDTO: ...

    @abc.abstractmethod
    async def get_courses_by_filters_v2(
        self,
        session: Any,
        current_user: UserDTO | None,
        limit: int,
        offset: int,
        tag: str | None = None,
        author: str | None = None,
        favorited: str | None = None,
    ) -> CoursesFeedDTO: ...

    @abc.abstractmethod
    async def update_course_by_slug(
        self,
        session: Any,
        slug: str,
        course_to_update: UpdateCourseDTO,
        current_user: UserDTO,
    ) -> CourseDTO: ...

    @abc.abstractmethod
    async def add_course_into_favorites(
        self, session: Any, slug: str, current_user: UserDTO
    ) -> CourseDTO: ...

    @abc.abstractmethod
    async def remove_course_from_favorites(
        self, session: Any, slug: str, current_user: UserDTO
    ) -> CourseDTO: ...
