"""Response schemas for audio generation API endpoints."""

from uuid import UUID

from pydantic import BaseModel, Field

from senda.domain.dtos.audio_generation import (
    AudioGenerationJobStatusResultDTO,
    AudioGenerationResultDTO,
    BatchAudioGenerationResultDTO,
    StartGenerationJobResultDTO,
)


class StartAudioGenerationResponse(BaseModel):
    """Response for async HLS audio generation start (HTTP 202)."""

    job_id: UUID = Field(..., description="ID of the audio generation job")
    lesson_id: int = Field(..., description="ID of the lesson")
    status: str = Field(..., description="Current job status")
    playlist_url: str = Field(..., description="Live HLS playlist URL for playback")

    @classmethod
    def from_dto(
        cls, dto: StartGenerationJobResultDTO
    ) -> "StartAudioGenerationResponse":
        return cls(
            job_id=dto.job_id,
            lesson_id=dto.lesson_id,
            status=dto.status.value,
            playlist_url=dto.playlist_url,
        )

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "lesson_id": 1,
                "status": "PENDING",
                "playlist_url": "https://cdn.senda.com/audio/1/job-id/playlist.m3u8",
            }
        }


class AudioGenerationJobStatusResponse(BaseModel):
    """Response for polling an HLS audio generation job."""

    job_id: UUID = Field(..., description="ID of the audio generation job")
    status: str = Field(..., description="Current job status")
    segments_available: int = Field(
        ..., description="Number of HLS segments uploaded so far"
    )
    available_duration_ms: int = Field(
        ..., description="Milliseconds of audio available in the uploaded HLS playlist"
    )
    estimated_total_duration_ms: int = Field(
        ..., description="Estimated final audio duration from the lesson script"
    )
    playlist_url: str = Field(..., description="Live or final HLS playlist URL")
    lesson_audio_id: UUID | None = Field(
        None, description="Published lesson_audio id when generation completes"
    )
    error_message: str | None = Field(
        None, description="Error details when status is FAILED"
    )

    @classmethod
    def from_dto(
        cls, dto: AudioGenerationJobStatusResultDTO
    ) -> "AudioGenerationJobStatusResponse":
        return cls(
            job_id=dto.job_id,
            status=dto.status.value,
            segments_available=dto.segments_available,
            available_duration_ms=dto.available_duration_ms,
            estimated_total_duration_ms=dto.estimated_total_duration_ms,
            playlist_url=dto.playlist_url,
            lesson_audio_id=dto.lesson_audio_id,
            error_message=dto.error_message,
        )

    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "status": "GENERATING",
                "segments_available": 3,
                "available_duration_ms": 18000,
                "estimated_total_duration_ms": 643000,
                "playlist_url": "https://cdn.senda.com/audio/1/job-id/playlist.m3u8",
                "lesson_audio_id": None,
                "error_message": None,
            }
        }


class AudioGenerationResponse(BaseModel):
    """Response for completed batch/synchronous audio generation."""

    lesson_id: int = Field(..., description="ID of the lesson")
    job_id: UUID = Field(..., description="ID of the completed generation job")
    playlist_url: str = Field(..., description="Final HLS playlist URL")
    generation_time_seconds: float = Field(
        ..., description="Time taken to generate the audio"
    )

    @classmethod
    def from_dto(cls, dto: AudioGenerationResultDTO) -> "AudioGenerationResponse":
        return cls(
            lesson_id=dto.lesson_id,
            job_id=dto.job_id,
            playlist_url=dto.playlist_url,
            generation_time_seconds=dto.generation_time_seconds,
        )

    class Config:
        json_schema_extra = {
            "example": {
                "lesson_id": 1,
                "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "playlist_url": "https://cdn.senda.com/audio/1/job-id/playlist.m3u8",
                "generation_time_seconds": 15.34,
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
        json_schema_extra = {
            "example": {
                "generated_audios": [
                    {
                        "lesson_id": 1,
                        "job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                        "playlist_url": "https://cdn.senda.com/audio/1/job-id/playlist.m3u8",
                        "generation_time_seconds": 15.34,
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
    """Response for lesson-level audio generation status check."""

    lesson_id: int = Field(..., description="ID of the lesson")
    status: str = Field(..., description="Current audio generation status")
    playlist_url: str | None = Field(
        None, description="HLS playlist URL if audio is available"
    )
    active_job_id: UUID | None = Field(
        None, description="Active generation job id while status is AUDIO_GENERATING"
    )
    available_duration_ms: int | None = Field(
        None,
        description="Milliseconds of audio available while generation is in progress",
    )
    estimated_total_duration_ms: int | None = Field(
        None,
        description="Estimated final audio duration while generation is in progress",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "lesson_id": 1,
                "status": "AUDIO_GENERATING",
                "playlist_url": "https://cdn.senda.com/audio/1/job-id/playlist.m3u8",
                "active_job_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "available_duration_ms": 18000,
                "estimated_total_duration_ms": 643000,
            }
        }
