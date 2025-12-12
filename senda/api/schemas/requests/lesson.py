from pydantic import BaseModel, Field

from senda.core.enums import LessonStatus, ScriptPartType
from senda.domain.dtos.lesson import (
    CreateLessonDTO,
    ReorderLessonDTO,
    ReorderLessonsDTO,
    UpdateLessonDTO,
)
from senda.domain.dtos.script_generation import ScriptPartDTO


class CreateLessonData(BaseModel):
    lesson_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1)
    core_practice: str = Field(..., min_length=1)
    key_point: str = Field(..., min_length=1)
    tone: str = Field(..., min_length=1)
    duration_minutes: int = Field(..., ge=1)


class UpdateLessonData(BaseModel):
    title: str | None = Field(None)
    core_practice: str | None = Field(None)
    key_point: str | None = Field(None)
    tone: str | None = Field(None)
    duration_minutes: int | None = Field(None, ge=1)
    status: str | None = Field(None)
    script: list[ScriptPartDTO] | None = Field(None)
    audio_url: str | None = Field(None)


class CreateLessonRequest(BaseModel):
    lesson: CreateLessonData

    def to_dto(self) -> CreateLessonDTO:
        return CreateLessonDTO(
            lesson_number=self.lesson.lesson_number,
            title=self.lesson.title,
            core_practice=self.lesson.core_practice,
            key_point=self.lesson.key_point,
            tone=self.lesson.tone,
            duration_minutes=self.lesson.duration_minutes,
        )


class UpdateLessonRequest(BaseModel):
    lesson: UpdateLessonData

    def to_dto(self) -> UpdateLessonDTO:
        script_parts = None
        if self.lesson.script is not None:
            try:
                script_parts = [
                    ScriptPartDTO(
                        type=part.type, content=part.content, duration=part.duration
                    )
                    for part in self.lesson.script
                ]
            except (KeyError, ValueError, TypeError):
                script_parts = None

        status_enum = None
        if self.lesson.status is not None:
            try:
                status_enum = LessonStatus(self.lesson.status)
            except ValueError:
                status_enum = None

        return UpdateLessonDTO(
            title=self.lesson.title,
            core_practice=self.lesson.core_practice,
            key_point=self.lesson.key_point,
            tone=self.lesson.tone,
            duration_minutes=self.lesson.duration_minutes,
            status=status_enum,
            script=script_parts,
            audio_url=self.lesson.audio_url,
        )


class ReorderLessonItem(BaseModel):
    lesson_id: int = Field(..., description="The ID of the lesson to reorder")
    lesson_number: int = Field(..., ge=1, description="The new position/order number")


class ReorderLessonsRequest(BaseModel):
    lessons: list[ReorderLessonItem] = Field(
        ..., min_length=1, description="List of lessons with their new order"
    )

    def to_dto(self) -> ReorderLessonsDTO:
        return ReorderLessonsDTO(
            lessons=[
                ReorderLessonDTO(
                    lesson_id=item.lesson_id, lesson_number=item.lesson_number
                )
                for item in self.lessons
            ]
        )


class BatchScriptGenerationRequest(BaseModel):
    lesson_ids: list[int] | None = Field(
        None,
        description="Optional list of lesson IDs to generate scripts for. "
        "If not provided, generates for all eligible lessons. "
        "If empty list, generates nothing.",
    )


class BatchAudioGenerationRequest(BaseModel):
    lesson_ids: list[int] | None = Field(
        None,
        description="Optional list of lesson IDs to generate audio for. "
        "If not provided, generates for all eligible lessons. "
        "If empty list, generates nothing.",
    )
