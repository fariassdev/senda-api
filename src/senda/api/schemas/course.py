from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from src.senda.api.models.course import LessonStatus


class LessonBase(BaseModel):
    lesson_number: int = Field(..., alias="lessonNumber")
    title: str
    core_practice: str = Field(..., alias="corePractice")
    key_point: str = Field(..., alias="keyPoint")
    tone: str
    duration_minutes: int = Field(..., alias="durationMinutes")

    class Config:
        populate_by_name = True


class LessonCreate(LessonBase):
    pass


class Lesson(LessonBase):
    id: int
    status: LessonStatus = LessonStatus.NOT_GENERATED
    script_url: Optional[HttpUrl] = Field(None, alias="scriptUrl")
    audio_url: Optional[HttpUrl] = Field(None, alias="audioUrl")

    class Config:
        from_attributes = True
        populate_by_name = True


class CourseBase(BaseModel):
    id: str
    title: str
    description: str
    author: str
    image_placeholder_url: Optional[HttpUrl] = Field(None, alias="imagePlaceholderUrl")

    class Config:
        populate_by_name = True


class CourseCreate(CourseBase):
    lessons: List[LessonCreate]


class Course(CourseBase):
    lessons: List[Lesson]

    class Config:
        from_attributes = True
        populate_by_name = True
