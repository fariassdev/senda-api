import datetime
from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class GenderEnum(str, Enum):
    FEMALE = "female"
    MALE = "male"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class VoiceDTO:
    """Domain representation of a Voice."""

    id: UUID
    name: str
    slug: str
    description: str | None
    language: str
    gender: GenderEnum
    reference_s3_key: str
    sample_s3_key: str | None
    reference_audio_url: str
    sample_audio_url: str | None
    tts_provider: str

    is_active: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime


@dataclass(frozen=True)
class CreateVoiceDTO:
    """DTO for creating a new voice."""

    name: str
    slug: str
    description: str | None
    language: str
    gender: GenderEnum
    tts_provider: str


@dataclass(frozen=True)
class UpdateVoiceDTO:
    """DTO for updating a voice."""

    is_active: bool | None = None
    description: str | None = None
    sample_s3_key: str | None = None
