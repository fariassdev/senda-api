import datetime
from dataclasses import dataclass, replace

from senda.domain.dtos.profile import ProfileDTO


@dataclass(frozen=True)
class CourseRecordDTO:
    """Raw course record from database."""

    id: int
    author_id: int
    slug: str
    title: str
    description: str
    difficulty_level: str
    active: bool
    image_placeholder_url: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


@dataclass(frozen=True)
class CourseAuthorDTO:
    """Course author information (User profile data)."""

    username: str
    bio: str | None = None
    image: str | None = None
    following: bool = False
    id: int | None = None


@dataclass(frozen=True)
class CourseDTO:
    """Full course DTO with author, tags, and favorites."""

    id: int
    author_id: int
    slug: str
    title: str
    description: str
    difficulty_level: str
    active: bool
    image_placeholder_url: str | None
    tags: list[str]
    author: CourseAuthorDTO
    created_at: datetime.datetime
    updated_at: datetime.datetime
    favorited: bool
    favorites_count: int

    @classmethod
    def with_updated_fields(cls, dto: "CourseDTO", updated_fields: dict) -> "CourseDTO":
        return replace(dto, **updated_fields)


@dataclass(frozen=True)
class CoursesFeedDTO:
    """List of courses with count."""

    courses: list[CourseDTO]
    courses_count: int


@dataclass(frozen=True)
class CreateCourseDTO:
    """DTO for creating a new course."""

    title: str
    description: str
    difficulty_level: str
    tags: list[str]
    active: bool = False
    image_placeholder_url: str | None = None


@dataclass(frozen=True)
class UpdateCourseDTO:
    """DTO for updating a course."""

    title: str | None = None
    description: str | None = None
    difficulty_level: str | None = None
    active: bool | None = None
    image_placeholder_url: str | None = None
