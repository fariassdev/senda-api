from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from src.senda.api.schemas.lesson import Lesson, LessonCreate


class CourseBase(BaseModel):
    title: str
    description: str
    tags: list[str]

    class Config:
        populate_by_name = True


class CourseCreate(CourseBase):
    lessons: list[LessonCreate]


class Course(CourseBase):
    id: int
    active: bool
    lessons: list[Lesson]
    author: str
    image_placeholder_url: Optional[HttpUrl] = Field(None, alias="imagePlaceholderUrl")

    class Config:
        from_attributes = True
        populate_by_name = True


class CourseCreatePrompt(BaseModel):
    prompt: str


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, alias="name")
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    active: Optional[bool] = None
    author: Optional[str] = None
    image_placeholder_url: Optional[HttpUrl] = Field(None, alias="imagePlaceholderUrl")

    class Config:
        populate_by_name = True
