import datetime
from dataclasses import dataclass
from uuid import UUID

from senda.core.enums import AudioGenerationJobStatus


@dataclass(frozen=True)
class AudioGenerationJobDTO:
    """Operational state for an HLS audio generation job."""

    id: UUID
    lesson_id: int
    voice_id: UUID | None
    voice_slug: str | None
    audio_provider: str | None
    s3_base_path: str
    status: AudioGenerationJobStatus
    segments_available: int
    lesson_audio_id: UUID | None
    error_message: str | None
    started_at: datetime.datetime | None
    completed_at: datetime.datetime | None
    created_at: datetime.datetime


@dataclass(frozen=True)
class CreateAudioGenerationJobDTO:
    """DTO for creating a new audio generation job."""

    id: UUID
    lesson_id: int
    voice_id: UUID
    voice_slug: str
    audio_provider: str
    s3_base_path: str


@dataclass(frozen=True)
class UpdateAudioGenerationJobDTO:
    """DTO for updating an audio generation job."""

    status: AudioGenerationJobStatus | None = None
    segments_available: int | None = None
    lesson_audio_id: UUID | None = None
    error_message: str | None = None
    started_at: datetime.datetime | None = None
    completed_at: datetime.datetime | None = None
