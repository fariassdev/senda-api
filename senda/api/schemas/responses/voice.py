import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from senda.core.utils.date import convert_datetime_to_realworld
from senda.domain.dtos.voice import VoiceDTO


class VoiceData(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None = None
    language: str
    gender: str
    reference_audio_url: str = Field(alias="referenceAudioUrl")
    sample_audio_url: str | None = Field(None, alias="sampleAudioUrl")
    tts_provider: str = Field(alias="ttsProvider")
    is_active: bool = Field(alias="isActive")
    is_synced_to_modal: bool = Field(alias="isSyncedToModal")
    modal_sync_error: str | None = Field(None, alias="modalSyncError")
    created_at: datetime.datetime = Field(alias="createdAt")
    updated_at: datetime.datetime = Field(alias="updatedAt")

    model_config = ConfigDict(
        json_encoders={datetime.datetime: convert_datetime_to_realworld}
    )


class VoiceResponse(BaseModel):
    voice: VoiceData

    @classmethod
    def from_dto(cls, dto: VoiceDTO) -> "VoiceResponse":
        voice = VoiceData(
            id=dto.id,
            name=dto.name,
            slug=dto.slug,
            description=dto.description,
            language=dto.language,
            gender=dto.gender.value,
            referenceAudioUrl=dto.reference_audio_url,
            sampleAudioUrl=dto.sample_audio_url,
            ttsProvider=dto.tts_provider,
            isActive=dto.is_active,
            isSyncedToModal=dto.is_synced_to_modal,
            modalSyncError=dto.modal_sync_error,
            createdAt=dto.created_at,
            updatedAt=dto.updated_at,
        )
        return VoiceResponse(voice=voice)
