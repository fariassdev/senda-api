from senda.domain.dtos.voice import GenderEnum, VoiceDTO
from senda.domain.mapper import IModelMapper
from senda.infrastructure.models import Voice


class VoiceModelMapper(IModelMapper[Voice, VoiceDTO]):
    """Mapper for Voice model."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def to_dto(self, model: Voice) -> VoiceDTO:
        return VoiceDTO(
            id=model.id,
            name=model.name,
            slug=model.slug,
            description=model.description,
            language=model.language,
            gender=GenderEnum(model.gender),
            reference_s3_key=model.reference_s3_key,
            sample_s3_key=model.sample_s3_key,
            reference_audio_url=f"{self._base_url}/{model.reference_s3_key}",
            sample_audio_url=f"{self._base_url}/{model.sample_s3_key}"
            if model.sample_s3_key
            else None,
            tts_provider=model.tts_provider,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def from_dto(self, dto: VoiceDTO) -> Voice:
        model = Voice(
            id=dto.id,
            name=dto.name,
            slug=dto.slug,
            description=dto.description,
            language=dto.language,
            gender=dto.gender.value,
            reference_s3_key=dto.reference_s3_key,
            sample_s3_key=dto.sample_s3_key,
            tts_provider=dto.tts_provider,
            is_active=dto.is_active,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )
        return model
