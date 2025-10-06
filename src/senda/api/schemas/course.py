from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from uuid import UUID
from src.senda.api.schemas.lesson import Lesson, LessonCreate
from datetime import datetime


class CourseBase(BaseModel):
    title: str
    description: str
    tags: list[str]

    model_config = dict(populate_by_name=True)


class CourseCreate(CourseBase):
    lessons: list[LessonCreate]


class Course(CourseBase):
    id: UUID
    active: bool
    lessons: list[Lesson]
    author: str
    image_placeholder_url: Optional[HttpUrl] = Field(None, alias="imagePlaceholderUrl")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    model_config = dict(from_attributes=True, populate_by_name=True)


class CourseCreatePrompt(BaseModel):
    prompt: str


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, alias="name")
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    active: Optional[bool] = None
    author: Optional[str] = None
    image_placeholder_url: Optional[HttpUrl] = Field(None, alias="imagePlaceholderUrl")

    model_config = dict(populate_by_name=True)
