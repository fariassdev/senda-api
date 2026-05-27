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
    exaggeration: float
    cfg_weight: float
    temperature: float
    is_active: bool
    is_synced_to_modal: bool
    modal_sync_error: str | None
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
    exaggeration: float
    cfg_weight: float
    temperature: float


@dataclass(frozen=True)
class UpdateVoiceDTO:
    """DTO for updating a voice."""

    exaggeration: float | None = None
    cfg_weight: float | None = None
    temperature: float | None = None
    is_active: bool | None = None
    description: str | None = None
    sample_s3_key: str | None = None
    is_synced_to_modal: bool | None = None
    modal_sync_error: str | None = None
