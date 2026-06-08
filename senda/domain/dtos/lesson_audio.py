import datetime
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class LessonAudioDTO:
    """Publishable HLS audio artifact for a lesson and voice."""

    id: UUID
    lesson_id: int
    voice_id: UUID | None
    voice_slug: str | None
    audio_provider: str | None
    playlist_url: str
    hls_base_path: str
    duration_ms: int
    generated_at: datetime.datetime
    created_at: datetime.datetime
    updated_at: datetime.datetime


@dataclass(frozen=True)
class UpsertLessonAudioDTO:
    """DTO for inserting or updating a completed lesson audio artifact."""

    lesson_id: int
    voice_id: UUID
    voice_slug: str
    audio_provider: str
    playlist_url: str
    hls_base_path: str
    duration_ms: int
    generated_at: datetime.datetime
