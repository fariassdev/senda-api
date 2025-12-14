"""Abstract interfaces for audio generation services."""

import abc

from senda.domain.dtos.audio_generation import (
    AudioGenerationRequestDTO,
    AudioGenerationResultDTO,
    BatchAudioGenerationResultDTO,
    CourseAudioGenerationRequestDTO,
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


class IAudioGenerationService(abc.ABC):
    """Business logic for audio generation."""

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
            InvalidLessonStateException: If lesson not in SCRIPT_COMPLETED state
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
