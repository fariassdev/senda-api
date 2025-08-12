from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from enum import Enum

from src.senda.api.models.course import LessonStatus


class ScriptPartType(str, Enum):
    SPEAK = "speak"
    PAUSE = "pause"


class ScriptPart(BaseModel):
    type: ScriptPartType
    content: Optional[str] = None
    duration: Optional[float] = None

    class Config:
        use_enum_values = True


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
    status: LessonStatus = LessonStatus.PENDING
    script: Optional[list[ScriptPart]] = None
    audio_url: Optional[HttpUrl] = Field(None, alias="audioUrl")

    class Config:
        from_attributes = True
        populate_by_name = True
