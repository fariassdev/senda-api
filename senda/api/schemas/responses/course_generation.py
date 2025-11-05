"""Response schemas for AI-powered course generation."""

import datetime

from pydantic import BaseModel, ConfigDict, Field

from senda.core.enums import DifficultyLevel
from senda.core.utils.date import convert_datetime_to_realworld
from senda.domain.dtos.course import CourseDTO
from senda.domain.dtos.lesson import LessonDTO


class LessonGenerationData(BaseModel):
    """Lesson data in course generation response."""

    lesson_number: int = Field(alias="lessonNumber")
    title: str
    core_practice: str = Field(alias="corePractice")
    key_point: str = Field(alias="keyPoint")
    tone: str
    duration_minutes: int = Field(alias="durationMinutes")
    status: str
    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")

    model_config = ConfigDict(
        json_encoders={datetime.datetime: convert_datetime_to_realworld}
    )


class CourseAuthorData(BaseModel):
    """Author data for course generation response."""

    username: str
    bio: str | None
    image: str | None
    following: bool


class CourseGenerationData(BaseModel):
    """Complete course data with lessons in generation response."""

    slug: str
    title: str
    description: str
    difficulty_level: DifficultyLevel = Field(alias="difficultyLevel")
    tags: list[str] = Field(alias="tagList")
    active: bool
    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")
    favorited: bool = False
    favorites_count: int = Field(default=0, alias="favoritesCount")
    author: CourseAuthorData
    lessons: list[LessonGenerationData]
    lessons_count: int = Field(alias="lessonsCount")

    model_config = ConfigDict(
        json_encoders={datetime.datetime: convert_datetime_to_realworld}
    )


class CourseGenerationResponse(BaseModel):
    """Response schema for successful course generation."""

    course: CourseGenerationData

    @classmethod
    def from_dto(
        cls, course_dto: CourseDTO, lessons: list[LessonDTO]
    ) -> "CourseGenerationResponse":
        """
        Converts domain DTOs to API response.

        Args:
            course_dto: CourseDTO from service layer
            lessons: List of LessonDTO for the course

        Returns:
            CourseGenerationResponse for API client
        """
        lessons_data = [
            LessonGenerationData(
                lessonNumber=lesson.lesson_number,
                title=lesson.title,
                corePractice=lesson.core_practice,
                keyPoint=lesson.key_point,
                tone=lesson.tone,
                durationMinutes=lesson.duration_minutes,
                status=lesson.status,
                createdAt=lesson.created_at,
                updatedAt=lesson.updated_at,
            )
            for lesson in lessons
        ]

        course_data = CourseGenerationData(
            slug=course_dto.slug,
            title=course_dto.title,
            description=course_dto.description,
            difficultyLevel=course_dto.difficulty_level,
            tagList=course_dto.tags,
            active=course_dto.active,
            createdAt=course_dto.created_at,
            updatedAt=course_dto.updated_at,
            favorited=course_dto.favorited,
            favoritesCount=course_dto.favorites_count,
            author=CourseAuthorData(
                username=course_dto.author.username,
                bio=course_dto.author.bio,
                image=course_dto.author.image,
                following=course_dto.author.following,
            ),
            lessons=lessons_data,
            lessonsCount=len(lessons),
        )

        return CourseGenerationResponse(course=course_data)
