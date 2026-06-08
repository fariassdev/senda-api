import datetime

from pydantic import BaseModel, ConfigDict, Field

from senda.api.schemas.responses.script_generation import ScriptPartResponse
from senda.core.utils.date import convert_datetime_to_realworld
from senda.domain.dtos.lesson import LessonDTO, LessonsListDTO


class LessonData(BaseModel):
    id: int
    lesson_number: int = Field(alias="lessonNumber")
    title: str
    core_practice: str = Field(alias="corePractice")
    key_point: str = Field(alias="keyPoint")
    tone: str
    duration_minutes: int = Field(alias="durationMinutes")
    status: str
    script: list[ScriptPartResponse] | None = None
    audio_url: str | None = Field(alias="audioUrl")
    script_generated_at: datetime.datetime | None = Field(alias="scriptGeneratedAt")
    audio_generated_at: datetime.datetime | None = Field(alias="audioGeneratedAt")
    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")

    model_config = ConfigDict(
        json_encoders={datetime.datetime: convert_datetime_to_realworld}
    )


class LessonResponse(BaseModel):
    lesson: LessonData

    @classmethod
    def from_dto(cls, dto: LessonDTO) -> "LessonResponse":
        lesson = LessonData(
            id=dto.id,
            lessonNumber=dto.lesson_number,
            title=dto.title,
            corePractice=dto.core_practice,
            keyPoint=dto.key_point,
            tone=dto.tone,
            durationMinutes=dto.duration_minutes,
            status=dto.status.value,
            script=[
                ScriptPartResponse(
                    type=part.type, content=part.content, duration=part.duration
                )
                for part in dto.script
            ]
            if dto.script
            else None,
            audioUrl=None,
            scriptGeneratedAt=dto.script_generated_at,
            audioGeneratedAt=None,
            createdAt=dto.created_at,
            updatedAt=dto.updated_at,
        )
        return LessonResponse(lesson=lesson)


class LessonsListResponse(BaseModel):
    lessons: list[LessonData]
    lessonsCount: int

    @classmethod
    def from_dto(cls, dto: LessonsListDTO) -> "LessonsListResponse":
        lessons = [
            LessonResponse.from_dto(dto=lesson_dto).lesson for lesson_dto in dto.lessons
        ]
        return LessonsListResponse(lessons=lessons, lessonsCount=dto.lessons_count)
