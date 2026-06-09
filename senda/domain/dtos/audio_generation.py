"""DTOs for audio generation feature."""

from dataclasses import dataclass
from uuid import UUID

from senda.core.enums import AudioGenerationJobStatus


@dataclass(frozen=True)
class AudioConfigDTO:
    """Configuration for audio generation (voice, speed)."""

    voice_id: UUID
    speed: float = 1.0  # Speech rate: 0.5 to 2.0


@dataclass(frozen=True)
class AudioGenerationRequestDTO:
    """Request to generate audio for a single lesson."""

    lesson_id: int
    user_id: int
    audio_config: AudioConfigDTO


@dataclass(frozen=True)
class CourseAudioGenerationRequestDTO:
    """Request to generate audio for all lessons in a course."""

    slug: str
    user_id: int
    audio_config: AudioConfigDTO
    lesson_ids: list[int] | None = None  # None = all, [] = none, [ids] = specific


@dataclass(frozen=True)
class StartGenerationJobResultDTO:
    """Result of initiating an HLS audio generation job."""

    job_id: UUID
    lesson_id: int
    status: AudioGenerationJobStatus
    playlist_url: str
    segments_available: int
    lesson_audio_id: UUID | None = None
    is_new: bool = False


@dataclass(frozen=True)
class AudioGenerationJobStatusResultDTO:
    """Current operational state for polling an HLS generation job."""

    job_id: UUID
    status: AudioGenerationJobStatus
    segments_available: int
    available_duration_ms: int
    estimated_total_duration_ms: int
    playlist_url: str
    lesson_audio_id: UUID | None
    error_message: str | None


@dataclass(frozen=True)
class AudioGenerationResultDTO:
    """Result of a completed HLS audio generation."""

    lesson_id: int
    job_id: UUID
    playlist_url: str
    generation_time_seconds: float

    @property
    def audio_url(self) -> str:
        """Temporary alias until API responses migrate to playlist_url."""
        return self.playlist_url


@dataclass(frozen=True)
class GenerationErrorDTO:
    """Error details for a failed generation attempt."""

    lesson_id: int
    error_type: str
    error_message: str


@dataclass
class BatchAudioGenerationResultDTO:
    """Result of batch audio generation including successes and errors."""

    results: list[AudioGenerationResultDTO]
    errors: list[GenerationErrorDTO]
    total_requested: int
