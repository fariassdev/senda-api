import datetime

from pydantic import BaseModel, ConfigDict, Field

from senda.core.utils.date import convert_datetime_to_realworld
from senda.domain.dtos.course import CourseDTO, CoursesFeedDTO


class CourseAuthorData(BaseModel):
    username: str
    bio: str | None
    image: str | None
    following: bool


class CourseData(BaseModel):
    slug: str
    title: str
    description: str
    difficulty_level: str = Field(alias="difficultyLevel")
    active: bool
    image_placeholder_url: str | None = Field(alias="imagePlaceholderUrl")
    tags: list[str] = Field(alias="tagList")
    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")
    favorited: bool = False
    favorites_count: int = Field(default=0, alias="favoritesCount")
    author: CourseAuthorData

    model_config = ConfigDict(
        json_encoders={datetime.datetime: convert_datetime_to_realworld}
    )


class CourseResponse(BaseModel):
    course: CourseData

    @classmethod
    def from_dto(cls, dto: CourseDTO) -> "CourseResponse":
        course = CourseData(
            slug=dto.slug,
            title=dto.title,
            description=dto.description,
            difficultyLevel=dto.difficulty_level,
            active=dto.active,
            imagePlaceholderUrl=dto.image_placeholder_url,
            tagList=dto.tags,
            createdAt=dto.created_at,
            updatedAt=dto.updated_at,
            favorited=dto.favorited,
            favoritesCount=dto.favorites_count,
            author=CourseAuthorData(
                username=dto.author.username,
                bio=dto.author.bio,
                image=dto.author.image,
                following=dto.author.following,
            ),
        )
        return CourseResponse(course=course)


class CoursesFeedResponse(BaseModel):
    courses: list[CourseData]
    courses_count: int = Field(alias="coursesCount")

    @classmethod
    def from_dto(cls, dto: CoursesFeedDTO) -> "CoursesFeedResponse":
        courses = [
            CourseResponse.from_dto(dto=course_dto).course for course_dto in dto.courses
        ]
        return CoursesFeedResponse(courses=courses, coursesCount=dto.courses_count)
