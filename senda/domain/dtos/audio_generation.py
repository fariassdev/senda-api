"""DTOs for audio generation feature."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioConfigDTO:
    """Configuration for audio generation (voice, speed)."""

    voice: str | None = None  # Voice override (e.g., "af_nicole", "af_bella")
    speed: float = 1.0  # Speech rate: 0.5 to 2.0


@dataclass(frozen=True)
class AudioGenerationRequestDTO:
    """Request to generate audio for a single lesson."""

    lesson_id: int
    user_id: int
    audio_config: AudioConfigDTO | None = None


@dataclass(frozen=True)
class CourseAudioGenerationRequestDTO:
    """Request to generate audio for all lessons in a course."""

    slug: str
    user_id: int
    lesson_ids: list[int] | None = None  # None = all, [] = none, [ids] = specific
    audio_config: AudioConfigDTO | None = None


@dataclass(frozen=True)
class AudioGenerationResultDTO:
    """Result of audio generation process."""

    lesson_id: int
    audio_url: str
    generation_time_seconds: float
    file_size_bytes: int | None = None


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
