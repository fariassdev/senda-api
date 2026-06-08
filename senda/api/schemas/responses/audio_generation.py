"""Response schemas for audio generation API endpoints."""

from pydantic import BaseModel, Field

from senda.domain.dtos.audio_generation import (
    AudioGenerationResultDTO,
    BatchAudioGenerationResultDTO,
)


class AudioGenerationResponse(BaseModel):
    """Response for audio generation request."""

    lesson_id: int = Field(..., description="ID of the lesson")
    audio_url: str = Field(..., description="Public URL of the generated audio file")
    generation_time_seconds: float = Field(
        ..., description="Time taken to generate the audio"
    )
    file_size_bytes: int = Field(..., description="Size of the audio file in bytes")

    @classmethod
    def from_dto(cls, dto: AudioGenerationResultDTO) -> "AudioGenerationResponse":
        """Create response from domain DTO."""
        return cls(
            lesson_id=dto.lesson_id,
            audio_url=dto.playlist_url,
            generation_time_seconds=dto.generation_time_seconds,
            file_size_bytes=dto.duration_ms,
        )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "lesson_id": 1,
                "audio_url": "https://senda-ai.s3.amazonaws.com/audio/1_welcome_to_senda_abc123.mp3",
                "generation_time_seconds": 15.34,
                "file_size_bytes": 524288,
            }
        }


class CourseAudiosGenerationResponse(BaseModel):
    """Response for bulk course audio generation."""

    generated_audios: list[AudioGenerationResponse] = Field(
        ..., description="List of generated audio results"
    )
    total_lessons_processed: int = Field(
        ..., description="Total number of lessons that were requested for processing"
    )
    successful_generations: int = Field(
        ..., description="Number of successful audio generations"
    )
    errors: list["GenerationErrorResponse"] = Field(
        default_factory=list, description="List of errors for failed generations"
    )

    @classmethod
    def from_batch_result(
        cls, batch_result: "BatchAudioGenerationResultDTO"
    ) -> "CourseAudiosGenerationResponse":
        """Create response from batch generation result DTO."""

        return cls(
            generated_audios=[
                AudioGenerationResponse.from_dto(dto) for dto in batch_result.results
            ],
            total_lessons_processed=batch_result.total_requested,
            successful_generations=len(batch_result.results),
            errors=[
                GenerationErrorResponse(
                    lesson_id=error.lesson_id,
                    error_type=error.error_type,
                    error_message=error.error_message,
                )
                for error in batch_result.errors
            ],
        )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "generated_audios": [
                    {
                        "lesson_id": 1,
                        "audio_url": "https://senda-ai.s3.amazonaws.com/audio/1_welcome_abc123.mp3",
                        "generation_time_seconds": 15.34,
                        "file_size_bytes": 524288,
                    }
                ],
                "total_lessons_processed": 5,
                "successful_generations": 1,
                "errors": [
                    {
                        "lesson_id": 2,
                        "error_type": "AudioProviderException",
                        "error_message": "TTS service unavailable",
                    }
                ],
            }
        }


class GenerationErrorResponse(BaseModel):
    """Error details for a failed generation attempt."""

    lesson_id: int = Field(..., description="ID of the lesson that failed")
    error_type: str = Field(..., description="Type/class of the error")
    error_message: str = Field(..., description="Human-readable error message")


class AudioGenerationStatusResponse(BaseModel):
    """Response for audio generation status check."""

    lesson_id: int = Field(..., description="ID of the lesson")
    status: str = Field(..., description="Current audio generation status")
    audio_url: str | None = Field(None, description="Audio URL if generation complete")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {"lesson_id": 1, "status": "AUDIO_GENERATING", "audio_url": None}
        }
