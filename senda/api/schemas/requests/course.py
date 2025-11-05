from pydantic import BaseModel, Field

from senda.domain.dtos.course import CreateCourseDTO, UpdateCourseDTO


class CoursesPagination(BaseModel):
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class CoursesFilters(BaseModel):
    tag: str | None = None
    author: str | None = None
    favorited: str | None = None


class CreateCourseData(BaseModel):
    title: str = Field(..., min_length=5)
    description: str = Field(min_length=10)
    difficulty_level: str = Field(default="BEGINNER")
    active: bool = Field(default=False)
    image_placeholder_url: str | None = Field(None)
    tags: list[str] = Field(alias="tagList", default_factory=list)


class UpdateCourseData(BaseModel):
    title: str | None = Field(None)
    description: str | None = Field(None)
    difficulty_level: str | None = Field(None)
    active: bool | None = Field(None)
    image_placeholder_url: str | None = Field(None)


class UpdateCourseRequest(BaseModel):
    course: UpdateCourseData

    def to_dto(self) -> UpdateCourseDTO:
        return UpdateCourseDTO(
            title=self.course.title,
            description=self.course.description,
            difficulty_level=self.course.difficulty_level,
            active=self.course.active,
            image_placeholder_url=self.course.image_placeholder_url,
        )


class CreateCourseRequest(BaseModel):
    course: CreateCourseData

    def to_dto(self) -> CreateCourseDTO:
        return CreateCourseDTO(
            title=self.course.title,
            description=self.course.description,
            difficulty_level=self.course.difficulty_level,
            active=self.course.active,
            image_placeholder_url=self.course.image_placeholder_url,
            tags=self.course.tags,
        )
