"""Audio generation service implementing business logic for lesson audio generation."""

import asyncio
import logging
import time
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.enums import LessonStatus, ScriptPartType
from senda.core.exceptions import (
    AudioGenerationException,
    AudioProviderException,
    CourseNotFoundException,
    InvalidLessonStateException,
    LessonNotFoundException,
    StorageProviderException,
    VoiceNotActiveException,
    VoiceNotFoundException,
)
from senda.domain.dtos.audio_generation import (
    AudioGenerationRequestDTO,
    AudioGenerationResultDTO,
    BatchAudioGenerationResultDTO,
    CourseAudioGenerationRequestDTO,
    GenerationErrorDTO,
)
from senda.domain.dtos.lesson import LessonRecordDTO, UpdateLessonDTO
from senda.domain.repositories.course import ICourseRepository
from senda.domain.repositories.lesson import ILessonRepository
from senda.domain.repositories.voice import IVoiceRepository
from senda.domain.services.audio_generation import (
    IAudioGenerationService,
    IAudioProvider,
    IStorageProvider,
)
from senda.domain.utils.script_serialization import LessonScript
from senda.infrastructure.utils.audio_processor import AudioProcessor

logger = logging.getLogger(__name__)


class AudioGenerationService(IAudioGenerationService):
    """Service to handle lesson audio generation logic."""

    def __init__(
        self,
        course_repo: ICourseRepository,
        lesson_repo: ILessonRepository,
        voice_repo: IVoiceRepository,
        storage_provider: IStorageProvider,
        audio_providers: dict[str, IAudioProvider],
        audio_processor: AudioProcessor | None = None,
        max_concurrent_lessons: int = 5,
        max_concurrent_tts: int = 3,
    ) -> None:
        self._course_repo = course_repo
        self._lesson_repo = lesson_repo
        self._voice_repo = voice_repo
        self._storage_provider = storage_provider
        self._audio_providers = audio_providers
        self._audio_processor = audio_processor or AudioProcessor()
        self._max_concurrent_lessons = max_concurrent_lessons
        self._max_concurrent_tts = max_concurrent_tts

    async def generate_lesson_audio(
        self, session: AsyncSession, request: AudioGenerationRequestDTO
    ) -> AudioGenerationResultDTO:
        """Generate and save audio for a single lesson.

        Raises:
            LessonNotFoundException: If lesson not found
            InvalidLessonStateException: If lesson not in SCRIPT_COMPLETED or AUDIO_COMPLETED state
            VoiceNotFoundException: If catalog voice does not exist
            VoiceNotActiveException: If catalog voice is inactive
            AudioProviderException: If TTS generation fails
            StorageProviderException: If storage upload fails
            AudioGenerationException: For other errors
        """
        logger.info(f"Starting audio generation for lesson {request.lesson_id}")
        start_time = time.time()

        lesson_record = await self._lesson_repo.get_or_none(
            session=session, lesson_id=request.lesson_id
        )
        if not lesson_record:
            raise LessonNotFoundException()

        if lesson_record.status not in [
            LessonStatus.SCRIPT_COMPLETED,
            LessonStatus.AUDIO_COMPLETED,
        ]:
            logger.warning(
                f"Lesson {request.lesson_id} not in SCRIPT_COMPLETED state: "
                f"{lesson_record.status}"
            )
            raise InvalidLessonStateException()

        course_record = await self._course_repo.get_by_id(
            session=session, course_id=lesson_record.course_id
        )
        if not course_record:
            raise CourseNotFoundException()

        voice_id = request.audio_config.voice_id
        speed = request.audio_config.speed

        catalog_voice = await self._voice_repo.get_or_none(
            session=session, voice_id=voice_id
        )
        if catalog_voice is None:
            raise VoiceNotFoundException()
        if not catalog_voice.is_active:
            raise VoiceNotActiveException()

        provider = self._audio_providers.get(catalog_voice.tts_provider)
        if not provider:
            raise AudioGenerationException(
                message=(
                    "No audio provider configured for provider type: "
                    f"{catalog_voice.tts_provider}"
                )
            )
        voice_name = catalog_voice.slug

        script_parts = LessonScript.deserialize(lesson_record.script)
        if not script_parts:
            logger.error(f"Lesson {request.lesson_id} has no script parts")
            raise AudioGenerationException(message="Lesson has no script content")

        try:
            await self._lesson_repo.update(
                session=session,
                lesson_id=request.lesson_id,
                update_item=UpdateLessonDTO(status=LessonStatus.AUDIO_GENERATING),
            )

            logger.info(
                f"Processing {len(script_parts)} script parts for lesson {request.lesson_id}"
            )

            semaphore = asyncio.Semaphore(self._max_concurrent_tts)

            async def generate_speech_with_semaphore(
                idx: int, text: str
            ) -> tuple[int, bytes]:
                async with semaphore:
                    logger.debug(f"Generating TTS for part {idx + 1}")
                    pcm_bytes = await provider.generate_speech(
                        text=text, voice=voice_name, speed=speed
                    )
                    return idx, pcm_bytes

            speak_tasks = []
            for idx, part in enumerate(script_parts):
                if (
                    part.type == ScriptPartType.SPEAK
                    and part.content
                    and part.content.strip()
                ):
                    speak_tasks.append(
                        generate_speech_with_semaphore(idx, part.content)
                    )

            logger.info(
                f"Generating TTS for {len(speak_tasks)} speak parts in parallel"
            )
            tts_results = await asyncio.gather(*speak_tasks)

            speech_data: dict[int, bytes] = {
                idx: pcm_bytes
                for idx, pcm_bytes in tts_results
                if pcm_bytes is not None
            }

            combined_audio = self._audio_processor.combine_script_parts(
                script_parts=script_parts, speech_data=speech_data
            )

            mp3_data = self._audio_processor.export_to_mp3(combined_audio)
            file_size = len(mp3_data)

            audio_url = await self._storage_provider.upload_audio(
                file_data=mp3_data,
                lesson_id=lesson_record.id,
                lesson_title=lesson_record.title,
            )

            await self._lesson_repo.update(
                session=session,
                lesson_id=request.lesson_id,
                update_item=UpdateLessonDTO(
                    audio_url=audio_url,
                    audio_generated_at=datetime.now(),
                    status=LessonStatus.AUDIO_COMPLETED,
                    voice_id=voice_id,
                ),
            )

            generation_time = time.time() - start_time
            logger.info(
                f"Successfully generated audio for lesson {request.lesson_id} "
                f"in {generation_time:.2f} seconds ({file_size} bytes)"
            )

            return AudioGenerationResultDTO(
                lesson_id=request.lesson_id,
                audio_url=audio_url,
                generation_time_seconds=generation_time,
                file_size_bytes=file_size,
            )

        except (AudioProviderException, StorageProviderException):
            await self._lesson_repo.update(
                session=session,
                lesson_id=request.lesson_id,
                update_item=UpdateLessonDTO(status=LessonStatus.AUDIO_FAILED),
            )
            raise

        except Exception as e:
            logger.exception(
                f"Unexpected error generating audio for lesson {request.lesson_id}: {e}"
            )
            await self._lesson_repo.update(
                session=session,
                lesson_id=request.lesson_id,
                update_item=UpdateLessonDTO(status=LessonStatus.AUDIO_FAILED),
            )
            if isinstance(e, AudioGenerationException):
                raise
            raise AudioGenerationException(
                message=f"Audio generation failed: {str(e)}"
            ) from e

    async def generate_course_audios(
        self, session: AsyncSession, request: CourseAudioGenerationRequestDTO
    ) -> BatchAudioGenerationResultDTO:
        """Generate audio for script-completed lessons in a course.

        This method processes lessons in parallel (up to max_concurrent_lessons at a time)
        for improved performance.

        Args:
            session: Database session
            request: Request with slug and optional lesson_ids
                - If lesson_ids is None: generate for all eligible lessons
                - If lesson_ids is []: generate nothing (return empty result)
                - If lesson_ids is [1, 2, 3]: generate only for those specific lessons

        Returns:
            BatchAudioGenerationResultDTO with successful results and any errors

        Raises:
            CourseNotFoundException: If course not found

        Note:
            This method continues processing even if individual lessons fail.
            Failed lessons are included in the errors list.
        """
        # Handle empty array case - explicit request to generate nothing
        if request.lesson_ids is not None and len(request.lesson_ids) == 0:
            logger.info(
                f"Empty lesson_ids provided for course {request.slug} - skipping generation"
            )
            return BatchAudioGenerationResultDTO(
                results=[], errors=[], total_requested=0
            )

        logger.info(f"Starting bulk audio generation for course {request.slug}")

        course_record = await self._course_repo.get_by_slug(
            session=session, slug=request.slug
        )

        all_lessons = await self._lesson_repo.list_by_course(
            session=session, course_id=course_record.id
        )

        ready_lessons = [
            lesson
            for lesson in all_lessons
            if lesson.status == LessonStatus.SCRIPT_COMPLETED
        ]

        # If specific lesson_ids provided, filter to only those lessons
        if request.lesson_ids is not None:
            ready_lessons = [
                lesson for lesson in ready_lessons if lesson.id in request.lesson_ids
            ]
            logger.info(
                f"Filtered to {len(ready_lessons)} lessons based on provided IDs"
            )

        if not ready_lessons:
            logger.info(
                f"No lessons ready for audio generation in course {request.slug}"
            )
            return BatchAudioGenerationResultDTO(
                results=[], errors=[], total_requested=0
            )

        logger.info(
            f"Found {len(ready_lessons)} lessons ready for audio generation "
            f"in course {request.slug} (max concurrent: {self._max_concurrent_lessons})"
        )

        # Create a semaphore to limit concurrent lesson processing
        semaphore = asyncio.Semaphore(self._max_concurrent_lessons)

        # Store errors in a list accessible from the inner function
        generation_errors: list[GenerationErrorDTO] = []

        async def process_lesson_with_semaphore(
            lesson_record: LessonRecordDTO,
        ) -> AudioGenerationResultDTO | None:
            """Process a single lesson with semaphore control."""
            async with semaphore:
                lesson_request = AudioGenerationRequestDTO(
                    lesson_id=lesson_record.id,
                    user_id=request.user_id,
                    audio_config=request.audio_config,
                )

                try:
                    result = await self.generate_lesson_audio(
                        session=session, request=lesson_request
                    )
                    logger.info(f"Generated audio for lesson {lesson_record.id}")
                    return result

                except Exception as e:
                    error_type = type(e).__name__
                    error_message = str(e)
                    logger.error(
                        f"Failed to generate audio for lesson {lesson_record.id}: {e}",
                        exc_info=True,
                    )
                    generation_errors.append(
                        GenerationErrorDTO(
                            lesson_id=lesson_record.id,
                            error_type=error_type,
                            error_message=error_message,
                        )
                    )
                    return None

        # Process all lessons in parallel (controlled by semaphore)
        results = await asyncio.gather(
            *[process_lesson_with_semaphore(lesson) for lesson in ready_lessons],
            return_exceptions=False,
        )

        # Filter out None results (failed generations)
        generated_results: list[AudioGenerationResultDTO] = [
            result for result in results if result is not None
        ]

        logger.info(
            f"Completed bulk generation for course {request.slug}: "
            f"{len(generated_results)}/{len(ready_lessons)} successful, "
            f"{len(generation_errors)} errors"
        )

        return BatchAudioGenerationResultDTO(
            results=generated_results,
            errors=generation_errors,
            total_requested=len(ready_lessons),
        )
