import json

from senda.core.enums import LessonStatus
from senda.domain.dtos.lesson import LessonRecordDTO
from senda.domain.mapper import IModelMapper
from senda.infrastructure.models import Lesson


class LessonModelMapper(IModelMapper[Lesson, LessonRecordDTO]):
    @staticmethod
    def to_dto(model: Lesson) -> LessonRecordDTO:
        dto = LessonRecordDTO(
            id=model.id,
            course_id=model.course_id,
            lesson_number=model.lesson_number,
            title=model.title,
            core_practice=model.core_practice,
            key_point=model.key_point,
            tone=model.tone,
            duration_minutes=model.duration_minutes,
            status=LessonStatus(model.status),
            script=model.script,
            audio_url=model.audio_url,
            script_generated_at=model.script_generated_at,
            audio_generated_at=model.audio_generated_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
        return dto

    @staticmethod
    def from_dto(dto: LessonRecordDTO) -> Lesson:
        model = Lesson(
            course_id=dto.course_id,
            lesson_number=dto.lesson_number,
            title=dto.title,
            core_practice=dto.core_practice,
            key_point=dto.key_point,
            tone=dto.tone,
            duration_minutes=dto.duration_minutes,
            status=dto.status.value,  # Convert enum to string for DB
            script=dto.script,
            audio_url=dto.audio_url,
            script_generated_at=dto.script_generated_at,
            audio_generated_at=dto.audio_generated_at,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )
        if hasattr(dto, "id"):
            model.id = dto.id
        return model
