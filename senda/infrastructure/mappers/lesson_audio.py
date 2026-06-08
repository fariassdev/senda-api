from senda.domain.dtos.lesson_audio import LessonAudioDTO
from senda.domain.mapper import IModelMapper
from senda.infrastructure.models import LessonAudio


class LessonAudioModelMapper(IModelMapper[LessonAudio, LessonAudioDTO]):
    def to_dto(self, model: LessonAudio) -> LessonAudioDTO:
        return LessonAudioDTO(
            id=model.id,
            lesson_id=model.lesson_id,
            voice_id=model.voice_id,
            voice_slug=model.voice_slug,
            audio_provider=model.audio_provider,
            playlist_url=model.playlist_url,
            hls_base_path=model.hls_base_path,
            segment_count=model.segment_count,
            duration_ms=model.duration_ms,
            generated_at=model.generated_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def from_dto(self, dto: LessonAudioDTO) -> LessonAudio:
        model = LessonAudio(
            lesson_id=dto.lesson_id,
            voice_id=dto.voice_id,
            voice_slug=dto.voice_slug,
            audio_provider=dto.audio_provider,
            playlist_url=dto.playlist_url,
            hls_base_path=dto.hls_base_path,
            segment_count=dto.segment_count,
            duration_ms=dto.duration_ms,
            generated_at=dto.generated_at,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )
        if hasattr(dto, "id"):
            model.id = dto.id
        return model
