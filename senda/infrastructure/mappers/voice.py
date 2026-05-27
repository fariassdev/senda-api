from senda.domain.dtos.voice import GenderEnum, VoiceDTO
from senda.domain.mapper import IModelMapper
from senda.infrastructure.models import Voice


class VoiceModelMapper(IModelMapper[Voice, VoiceDTO]):
    """Mapper for Voice model."""

    @staticmethod
    def to_dto(model: Voice) -> VoiceDTO:
        return VoiceDTO(
            id=model.id,
            name=model.name,
            slug=model.slug,
            description=model.description,
            language=model.language,
            gender=GenderEnum(model.gender),
            reference_s3_key=model.reference_s3_key,
            sample_s3_key=model.sample_s3_key,
            exaggeration=model.exaggeration,
            cfg_weight=model.cfg_weight,
            temperature=model.temperature,
            is_active=model.is_active,
            is_synced_to_modal=model.is_synced_to_modal,
            modal_sync_error=model.modal_sync_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def from_dto(dto: VoiceDTO) -> Voice:
        model = Voice(
            id=dto.id,
            name=dto.name,
            slug=dto.slug,
            description=dto.description,
            language=dto.language,
            gender=dto.gender.value,
            reference_s3_key=dto.reference_s3_key,
            sample_s3_key=dto.sample_s3_key,
            exaggeration=dto.exaggeration,
            cfg_weight=dto.cfg_weight,
            temperature=dto.temperature,
            is_active=dto.is_active,
            is_synced_to_modal=dto.is_synced_to_modal,
            modal_sync_error=dto.modal_sync_error,
            created_at=dto.created_at,
            updated_at=dto.updated_at,
        )
        return model
