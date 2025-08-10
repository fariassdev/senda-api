from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from src.senda.api.models.course import LessonStatus

# region Lesson Schemas


class LessonBase(BaseModel):
    lesson_number: int = Field(..., alias="lessonNumber")
    title: str
    core_practice: str = Field(..., alias="corePractice")
    duration_minutes: int = Field(..., alias="durationMinutes")
    key_point: str = Field(..., alias="keyPoint")
    tone: str

    class Config:
        populate_by_name = True


class LessonCreate(LessonBase):
    pass


class Lesson(LessonBase):
    id: int
    status: LessonStatus = LessonStatus.NOT_GENERATED
    script: Optional[List[Dict[str, Any]]] = Field(None)
    audio_url: Optional[HttpUrl] = Field(None, alias="audioUrl")

    class Config:
        from_attributes = True
        populate_by_name = True


# endregion

# region Course Schemas


class CourseBase(BaseModel):
    title: str = Field(..., alias="name")
    description: str
    total_lessons: int = Field(..., alias="totalLessons")
    tags: List[str]

    class Config:
        populate_by_name = True


class CourseCreate(CourseBase):
    lessons: List[LessonCreate]


class Course(CourseBase):
    id: int
    active: bool
    lessons: List[Lesson]
    author: str  # Assuming author is added after creation
    image_placeholder_url: Optional[HttpUrl] = Field(None, alias="imagePlaceholderUrl")

    class Config:
        from_attributes = True
        populate_by_name = True


class CourseCreatePrompt(BaseModel):
    prompt: str


class CourseUpdate(BaseModel):
    title: Optional[str] = Field(None, alias="name")
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    active: Optional[bool] = None
    author: Optional[str] = None
    image_placeholder_url: Optional[HttpUrl] = Field(None, alias="imagePlaceholderUrl")

    class Config:
        populate_by_name = True


# endregion
