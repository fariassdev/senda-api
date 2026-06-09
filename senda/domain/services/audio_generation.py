"""Abstract interfaces for audio generation services."""

import abc
from uuid import UUID

from senda.domain.dtos.audio_generation import (
    AudioGenerationJobStatusResultDTO,
    AudioGenerationRequestDTO,
    AudioGenerationResultDTO,
    BatchAudioGenerationResultDTO,
    CourseAudioGenerationRequestDTO,
    StartGenerationJobResultDTO,
)


class IAudioProvider(abc.ABC):
    """Abstract interface for text-to-speech generation."""

    @abc.abstractmethod
    async def generate_speech(
        self, text: str, voice: str | None = None, speed: float = 1.0
    ) -> bytes:
        """Generate audio from text, return raw audio bytes.

        Args:
            text: Text to convert to speech
            voice: Optional voice override (uses provider default if None)
            speed: Speech rate multiplier (0.5 to 2.0, default 1.0)

        Returns:
            Raw audio bytes (PCM format)

        Raises:
            AudioProviderException: If TTS generation fails
        """
        pass


class IStorageProvider(abc.ABC):
    """Abstract interface for file storage (S3, local, etc.)."""

    @abc.abstractmethod
    async def upload_audio(
        self, file_data: bytes, lesson_id: int, lesson_title: str
    ) -> str:
        """Upload audio file to storage, return public URL.

        Args:
            file_data: Audio file data to upload
            lesson_id: ID of the lesson for filename generation
            lesson_title: Title of the lesson for filename generation

        Returns:
            Public URL of the uploaded audio file

        Raises:
            StorageProviderException: If upload fails
        """
        pass

    @abc.abstractmethod
    async def upload_file(
        self,
        file_data: bytes,
        key: str,
        content_type: str,
        cache_control: str | None = None,
    ) -> str:
        """Upload a file to storage at a specific key location.

        Args:
            file_data: Raw bytes of the file to upload
            key: Target path/key in storage
            content_type: Content-Type MIME type string
            cache_control: Optional Cache-Control header for CDN behavior

        Returns:
            Public URL of the uploaded file

        Raises:
            StorageProviderException: If upload fails
        """
        pass

    @abc.abstractmethod
    def public_url_for_key(self, key: str) -> str:
        """Build the public URL for an object key without uploading."""
        pass

    @abc.abstractmethod
    async def delete_file(self, key: str) -> None:
        """Delete a file from storage by object key.

        Raises:
            StorageProviderException: If deletion fails
        """
        pass


class IAudioGenerationService(abc.ABC):
    """Business logic for audio generation."""

    @abc.abstractmethod
    async def start_generation_job(
        self, session: object, request: AudioGenerationRequestDTO
    ) -> StartGenerationJobResultDTO:
        """Create or return an active HLS generation job for a lesson."""
        pass

    @abc.abstractmethod
    async def run_generation_pipeline(self, job_id: UUID) -> None:
        """Run the long-running TTS + HLS pipeline for a job."""
        pass

    @abc.abstractmethod
    async def get_job_status(
        self, session: object, job_id: UUID
    ) -> AudioGenerationJobStatusResultDTO:
        """Return current job status for CMS polling."""
        pass

    @abc.abstractmethod
    async def get_active_job_for_lesson(
        self, session: object, lesson_id: int
    ) -> AudioGenerationJobStatusResultDTO | None:
        """Return the active generation job for a lesson, if any."""
        pass

    @abc.abstractmethod
    async def generate_lesson_audio(
        self, session: object, request: AudioGenerationRequestDTO
    ) -> AudioGenerationResultDTO:
        """Generate audio for a single lesson.

        Args:
            session: Database session
            request: Audio generation request with lesson_id and user_id

        Returns:
            AudioGenerationResultDTO with audio URL and metrics

        Raises:
            LessonNotFoundException: If lesson not found
            InvalidLessonStateException: If lesson not in SCRIPT_COMPLETED or AUDIO_COMPLETED state
            AudioProviderException: If TTS generation fails
            StorageProviderException: If storage upload fails
            AudioGenerationException: For other errors
        """
        pass

    @abc.abstractmethod
    async def generate_course_audios(
        self, session: object, request: CourseAudioGenerationRequestDTO
    ) -> BatchAudioGenerationResultDTO:
        """Generate audio for all script-completed lessons in a course.

        Args:
            session: Database session
            request: Course audio generation request

        Returns:
            BatchAudioGenerationResultDTO with successful results and any errors

        Raises:
            CourseNotFoundException: If course not found

        Note:
            This method continues processing even if individual lessons fail.
            Failed lessons are included in the errors list.
        """
        pass
