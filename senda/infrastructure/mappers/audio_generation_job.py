from senda.core.enums import AudioGenerationJobStatus
from senda.domain.dtos.audio_generation_job import AudioGenerationJobDTO
from senda.domain.mapper import IModelMapper
from senda.infrastructure.models import AudioGenerationJob


class AudioGenerationJobModelMapper(
    IModelMapper[AudioGenerationJob, AudioGenerationJobDTO]
):
    def to_dto(self, model: AudioGenerationJob) -> AudioGenerationJobDTO:
        return AudioGenerationJobDTO(
            id=model.id,
            lesson_id=model.lesson_id,
            voice_id=model.voice_id,
            voice_slug=model.voice_slug,
            audio_provider=model.audio_provider,
            s3_base_path=model.s3_base_path,
            speed=model.speed,
            status=AudioGenerationJobStatus(model.status),
            segments_available=model.segments_available,
            segment_count=model.segment_count,
            duration_ms=model.duration_ms,
            lesson_audio_id=model.lesson_audio_id,
            error_message=model.error_message,
            started_at=model.started_at,
            completed_at=model.completed_at,
            created_at=model.created_at,
        )

    def from_dto(self, dto: AudioGenerationJobDTO) -> AudioGenerationJob:
        model = AudioGenerationJob(
            lesson_id=dto.lesson_id,
            voice_id=dto.voice_id,
            voice_slug=dto.voice_slug,
            audio_provider=dto.audio_provider,
            s3_base_path=dto.s3_base_path,
            speed=dto.speed,
            status=dto.status.value,
            segments_available=dto.segments_available,
            segment_count=dto.segment_count,
            duration_ms=dto.duration_ms,
            lesson_audio_id=dto.lesson_audio_id,
            error_message=dto.error_message,
            started_at=dto.started_at,
            completed_at=dto.completed_at,
            created_at=dto.created_at,
        )
        if hasattr(dto, "id"):
            model.id = dto.id
        return model
