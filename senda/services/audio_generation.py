"""Audio generation service implementing business logic for lesson audio generation."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from senda.core.enums import (
    AudioGenerationJobStatus,
    LessonStatus,
    ScriptPartType,
    TtsProvider,
)
from senda.core.exceptions import (
    AudioGenerationException,
    AudioProviderException,
    InvalidLessonStateException,
    LessonNotFoundException,
    StorageProviderException,
    VoiceNotActiveException,
    VoiceNotFoundException,
)
from senda.domain.dtos.audio_generation import (
    AudioGenerationJobStatusResultDTO,
    AudioGenerationRequestDTO,
    AudioGenerationResultDTO,
    BatchAudioGenerationResultDTO,
    CourseAudioGenerationRequestDTO,
    GenerationErrorDTO,
    StartGenerationJobResultDTO,
)
from senda.domain.dtos.audio_generation_job import (
    AudioGenerationJobDTO,
    CreateAudioGenerationJobDTO,
    UpdateAudioGenerationJobDTO,
)
from senda.domain.dtos.lesson import LessonRecordDTO, UpdateLessonDTO
from senda.domain.dtos.lesson_audio import UpsertLessonAudioDTO
from senda.domain.dtos.script_generation import ScriptPartDTO
from senda.domain.dtos.voice import VoiceDTO
from senda.domain.repositories.audio_generation_job import IAudioGenerationJobRepository
from senda.domain.repositories.course import ICourseRepository
from senda.domain.repositories.lesson import ILessonRepository
from senda.domain.repositories.lesson_audio import ILessonAudioRepository
from senda.domain.repositories.voice import IVoiceRepository
from senda.domain.services.audio_generation import (
    IAudioGenerationService,
    IAudioProvider,
    IStorageProvider,
)
from senda.domain.utils.script_duration import estimate_script_duration_ms
from senda.domain.utils.script_serialization import LessonScript
from senda.infrastructure.audio.composer import (
    AudioComposer,
    SegmentProgress,
    playlist_url_for,
)
from senda.infrastructure.utils.audio_processor import AudioProcessor

logger = logging.getLogger(__name__)


def s3_base_path_for(lesson_id: int, job_id: UUID) -> str:
    return f"audio/{lesson_id}/{job_id}/"


class AudioGenerationService(IAudioGenerationService):
    """Service to handle lesson HLS audio generation."""

    def __init__(
        self,
        course_repo: ICourseRepository,
        lesson_repo: ILessonRepository,
        voice_repo: IVoiceRepository,
        job_repo: IAudioGenerationJobRepository,
        lesson_audio_repo: ILessonAudioRepository,
        storage_provider: IStorageProvider,
        audio_composer: AudioComposer,
        audio_providers: dict[TtsProvider, IAudioProvider],
        session_factory: async_sessionmaker[AsyncSession],
        cdn_base_url: str | None = None,
        audio_processor: AudioProcessor | None = None,
        max_concurrent_lessons: int = 5,
        max_concurrent_tts: int = 3,
    ) -> None:
        self._course_repo = course_repo
        self._lesson_repo = lesson_repo
        self._voice_repo = voice_repo
        self._job_repo = job_repo
        self._lesson_audio_repo = lesson_audio_repo
        self._storage_provider = storage_provider
        self._audio_composer = audio_composer
        self._audio_providers = audio_providers
        self._session_factory = session_factory
        self._cdn_base_url = cdn_base_url
        self._audio_processor = audio_processor or AudioProcessor()
        self._max_concurrent_lessons = max_concurrent_lessons
        self._max_concurrent_tts = max_concurrent_tts

    def _resolve_cdn_base_url(self) -> str:
        if self._cdn_base_url:
            return self._cdn_base_url.rstrip("/")
        return self._storage_provider.public_url_for_key("").rstrip("/")

    def _resolve_audio_provider(self, tts_provider: str) -> IAudioProvider:
        try:
            provider_key = TtsProvider(tts_provider)
        except ValueError:
            raise AudioGenerationException(
                message=f"Unknown TTS provider: {tts_provider}"
            ) from None

        provider = self._audio_providers.get(provider_key)
        if provider is None:
            raise AudioGenerationException(
                message=f"No audio provider configured for provider type: {tts_provider}"
            )
        return provider

    def _job_to_start_result(
        self, job: AudioGenerationJobDTO, *, is_new: bool = False
    ) -> StartGenerationJobResultDTO:
        return StartGenerationJobResultDTO(
            job_id=job.id,
            lesson_id=job.lesson_id,
            status=job.status,
            playlist_url=playlist_url_for(
                self._resolve_cdn_base_url(), job.s3_base_path
            ),
            segments_available=job.segments_available,
            lesson_audio_id=job.lesson_audio_id,
            is_new=is_new,
        )

    async def get_job_status(
        self, session: AsyncSession, job_id: UUID
    ) -> AudioGenerationJobStatusResultDTO:
        job = await self._job_repo.get(session=session, job_id=job_id)
        return self._job_to_status_result(job)

    async def get_active_job_for_lesson(
        self, session: AsyncSession, lesson_id: int
    ) -> AudioGenerationJobStatusResultDTO | None:
        job = await self._job_repo.get_active_for_lesson(
            session=session, lesson_id=lesson_id
        )
        if job is None:
            return None
        return self._job_to_status_result(job)

    def _job_to_status_result(
        self, job: AudioGenerationJobDTO
    ) -> AudioGenerationJobStatusResultDTO:
        return AudioGenerationJobStatusResultDTO(
            job_id=job.id,
            status=job.status,
            segments_available=job.segments_available,
            available_duration_ms=job.available_duration_ms,
            estimated_total_duration_ms=job.estimated_total_duration_ms,
            playlist_url=playlist_url_for(
                self._resolve_cdn_base_url(), job.s3_base_path
            ),
            lesson_audio_id=job.lesson_audio_id,
            error_message=job.error_message,
        )

    async def _validate_lesson_for_generation(
        self, session: AsyncSession, lesson_id: int
    ) -> LessonRecordDTO:
        lesson_record = await self._lesson_repo.get_or_none(
            session=session, lesson_id=lesson_id
        )
        if not lesson_record:
            raise LessonNotFoundException()

        if lesson_record.status not in [
            LessonStatus.SCRIPT_COMPLETED,
            LessonStatus.AUDIO_COMPLETED,
            LessonStatus.AUDIO_FAILED,
        ]:
            logger.warning(
                "Lesson %s not ready for audio generation: %s",
                lesson_id,
                lesson_record.status,
            )
            raise InvalidLessonStateException()
        return lesson_record

    async def _validate_voice(self, session: AsyncSession, voice_id: UUID) -> VoiceDTO:
        catalog_voice = await self._voice_repo.get_or_none(
            session=session, voice_id=voice_id
        )
        if catalog_voice is None:
            raise VoiceNotFoundException()
        if not catalog_voice.is_active:
            raise VoiceNotActiveException()
        return catalog_voice

    async def start_generation_job(
        self, session: AsyncSession, request: AudioGenerationRequestDTO
    ) -> StartGenerationJobResultDTO:
        """Create or return an active HLS generation job (idempotent per lesson+voice)."""
        lesson_record = await self._validate_lesson_for_generation(
            session=session, lesson_id=request.lesson_id
        )
        catalog_voice = await self._validate_voice(
            session=session, voice_id=request.audio_config.voice_id
        )

        script_parts = LessonScript.deserialize(lesson_record.script)
        if not script_parts:
            raise AudioGenerationException(message="Lesson has no script content")

        voice_id = request.audio_config.voice_id
        existing_job = await self._job_repo.get_active_for_lesson_voice(
            session=session, lesson_id=request.lesson_id, voice_id=voice_id
        )
        if existing_job:
            logger.info(
                "Returning existing active job %s for lesson %s",
                existing_job.id,
                request.lesson_id,
            )
            return self._job_to_start_result(existing_job, is_new=False)

        estimated_total_duration_ms = estimate_script_duration_ms(
            script_parts, target_duration_minutes=lesson_record.duration_minutes
        )

        job_id = uuid4()
        create_item = CreateAudioGenerationJobDTO(
            id=job_id,
            lesson_id=request.lesson_id,
            voice_id=voice_id,
            voice_slug=catalog_voice.slug,
            audio_provider=catalog_voice.tts_provider,
            s3_base_path=s3_base_path_for(request.lesson_id, job_id),
            estimated_total_duration_ms=estimated_total_duration_ms,
        )

        try:
            job = await self._job_repo.add(session=session, create_item=create_item)
        except IntegrityError:
            await session.rollback()
            raced_job = await self._job_repo.get_active_for_lesson_voice(
                session=session, lesson_id=request.lesson_id, voice_id=voice_id
            )
            if raced_job is None:
                raise
            return self._job_to_start_result(raced_job, is_new=False)

        logger.info(
            "Created audio generation job %s for lesson %s", job.id, request.lesson_id
        )
        return self._job_to_start_result(job, is_new=True)

    async def run_generation_pipeline(self, job_id: UUID) -> None:
        """Run TTS + HLS composition and persist job/lesson outcomes."""
        speech_tasks: dict[int, asyncio.Task[tuple[int, bytes | None]]] = {}
        try:
            async with self._session_factory() as session:
                job = await self._job_repo.get(session=session, job_id=job_id)
                lesson_record = await self._lesson_repo.get(
                    session=session, lesson_id=job.lesson_id
                )
                if job.voice_id is None:
                    raise AudioGenerationException(message="Job is missing voice_id")
                catalog_voice = await self._validate_voice(
                    session=session, voice_id=job.voice_id
                )
                script_parts = LessonScript.deserialize(lesson_record.script)
                if not script_parts:
                    raise AudioGenerationException(
                        message="Lesson has no script content"
                    )

                estimated_total_duration_ms = estimate_script_duration_ms(
                    script_parts, target_duration_minutes=lesson_record.duration_minutes
                )

                now = datetime.now()
                await self._lesson_repo.update(
                    session=session,
                    lesson_id=job.lesson_id,
                    update_item=UpdateLessonDTO(status=LessonStatus.AUDIO_GENERATING),
                )
                await self._job_repo.update(
                    session=session,
                    job_id=job_id,
                    update_item=UpdateAudioGenerationJobDTO(
                        status=AudioGenerationJobStatus.GENERATING,
                        started_at=now,
                        estimated_total_duration_ms=estimated_total_duration_ms,
                    ),
                )
                await session.commit()

                s3_base_path = job.s3_base_path
                lesson_id = job.lesson_id
                voice_id = job.voice_id
                voice_slug = job.voice_slug or catalog_voice.slug
                audio_provider = job.audio_provider or catalog_voice.tts_provider

            provider = self._resolve_audio_provider(catalog_voice.tts_provider)

            # Dispatch TTS requests as concurrent tasks
            semaphore = asyncio.Semaphore(self._max_concurrent_tts)

            async def generate_speech_with_semaphore(
                idx: int, text: str
            ) -> tuple[int, bytes | None]:
                async with semaphore:
                    try:
                        pcm_bytes = await provider.generate_speech(
                            text=text, voice=catalog_voice.slug
                        )
                        return idx, pcm_bytes
                    except AudioProviderException as exc:
                        logger.warning(
                            "TTS failed for script part %s, composer will use silence: %s",
                            idx + 1,
                            exc,
                        )
                        return idx, None

            for idx, part in enumerate(script_parts):
                if (
                    part.type == ScriptPartType.SPEAK
                    and part.content
                    and part.content.strip()
                ):
                    speech_tasks[idx] = asyncio.create_task(
                        generate_speech_with_semaphore(idx, part.content)
                    )

            async def get_speech_for_part(idx: int) -> bytes | None:
                task = speech_tasks.get(idx)
                if task is None:
                    return None
                _, pcm_bytes = await task
                return pcm_bytes

            async def on_segment_ready(progress: SegmentProgress) -> None:
                async with self._session_factory() as progress_session:
                    await self._job_repo.update(
                        session=progress_session,
                        job_id=job_id,
                        update_item=UpdateAudioGenerationJobDTO(
                            segments_available=progress.segments_available,
                            available_duration_ms=progress.available_duration_ms,
                        ),
                    )
                    await progress_session.commit()

            composition = await self._audio_composer.compose_hls(
                job_id=job_id,
                script_parts=script_parts,
                speech_data=get_speech_for_part,
                s3_base_path=s3_base_path,
                cdn_base_url=self._resolve_cdn_base_url(),
                on_segment_ready=on_segment_ready,
            )

            # Ensure all background tasks are fully completed
            if speech_tasks:
                await asyncio.gather(*speech_tasks.values(), return_exceptions=True)

            async with self._session_factory() as session:
                completed_at = datetime.now()
                lesson_audio = await self._lesson_audio_repo.upsert(
                    session=session,
                    upsert_item=UpsertLessonAudioDTO(
                        lesson_id=lesson_id,
                        voice_id=voice_id,
                        voice_slug=voice_slug,
                        audio_provider=audio_provider,
                        playlist_url=composition.playlist_url,
                        hls_base_path=s3_base_path,
                        duration_ms=composition.duration_ms,
                        generated_at=completed_at,
                    ),
                )
                await self._job_repo.update(
                    session=session,
                    job_id=job_id,
                    update_item=UpdateAudioGenerationJobDTO(
                        status=AudioGenerationJobStatus.COMPLETED,
                        lesson_audio_id=lesson_audio.id,
                        available_duration_ms=composition.duration_ms,
                        completed_at=completed_at,
                    ),
                )
                await self._lesson_repo.update(
                    session=session,
                    lesson_id=lesson_id,
                    update_item=UpdateLessonDTO(status=LessonStatus.AUDIO_COMPLETED),
                )
                await session.commit()

            logger.info(
                "Completed HLS generation job %s for lesson %s", job_id, lesson_id
            )
        except Exception as exc:
            # Clean up any pending tasks in case of error
            for task in speech_tasks.values():
                if not task.done():
                    task.cancel()
            if speech_tasks:
                await asyncio.gather(*speech_tasks.values(), return_exceptions=True)

            error_message = str(exc)
            logger.exception("HLS generation job %s failed: %s", job_id, exc)
            async with self._session_factory() as session:
                failed_job = await self._job_repo.get_or_none(
                    session=session, job_id=job_id
                )
                if failed_job:
                    await self._job_repo.update(
                        session=session,
                        job_id=job_id,
                        update_item=UpdateAudioGenerationJobDTO(
                            status=AudioGenerationJobStatus.FAILED,
                            error_message=error_message,
                        ),
                    )
                    await self._lesson_repo.update(
                        session=session,
                        lesson_id=failed_job.lesson_id,
                        update_item=UpdateLessonDTO(status=LessonStatus.AUDIO_FAILED),
                    )
                    await session.commit()

    async def generate_lesson_audio(
        self, session: AsyncSession, request: AudioGenerationRequestDTO
    ) -> AudioGenerationResultDTO:
        """Start a job and run the HLS pipeline to completion (blocking)."""
        logger.info("Starting HLS audio generation for lesson %s", request.lesson_id)
        start_time = time.time()

        start_result = await self.start_generation_job(session=session, request=request)
        await self.run_generation_pipeline(start_result.job_id)

        job = await self._job_repo.get(session=session, job_id=start_result.job_id)
        if job.status == AudioGenerationJobStatus.FAILED:
            raise AudioGenerationException(
                message=job.error_message or "Audio generation failed"
            )

        generation_time = time.time() - start_time
        logger.info(
            "Successfully generated HLS audio for lesson %s in %.2f seconds",
            request.lesson_id,
            generation_time,
        )

        return AudioGenerationResultDTO(
            lesson_id=request.lesson_id,
            job_id=job.id,
            playlist_url=start_result.playlist_url,
            generation_time_seconds=generation_time,
        )

    async def generate_course_audios(
        self, session: AsyncSession, request: CourseAudioGenerationRequestDTO
    ) -> BatchAudioGenerationResultDTO:
        """Generate HLS audio for script-completed lessons in a course."""
        if request.lesson_ids is not None and len(request.lesson_ids) == 0:
            logger.info(
                "Empty lesson_ids provided for course %s - skipping generation",
                request.slug,
            )
            return BatchAudioGenerationResultDTO(
                results=[], errors=[], total_requested=0
            )

        logger.info("Starting bulk HLS audio generation for course %s", request.slug)

        course_record = await self._course_repo.get_by_slug(
            session=session, slug=request.slug
        )
        all_lessons = await self._lesson_repo.list_by_course(
            session=session, course_id=course_record.id
        )

        ready_lessons = [
            lesson
            for lesson in all_lessons
            if lesson.status
            in [LessonStatus.SCRIPT_COMPLETED, LessonStatus.AUDIO_FAILED]
        ]

        if request.lesson_ids is not None:
            ready_lessons = [
                lesson for lesson in ready_lessons if lesson.id in request.lesson_ids
            ]

        if not ready_lessons:
            return BatchAudioGenerationResultDTO(
                results=[], errors=[], total_requested=0
            )

        semaphore = asyncio.Semaphore(self._max_concurrent_lessons)
        generation_errors: list[GenerationErrorDTO] = []

        async def process_lesson_with_semaphore(
            lesson_record: LessonRecordDTO,
        ) -> AudioGenerationResultDTO | None:
            async with semaphore:
                lesson_request = AudioGenerationRequestDTO(
                    lesson_id=lesson_record.id,
                    user_id=request.user_id,
                    audio_config=request.audio_config,
                )
                try:
                    async with self._session_factory() as lesson_session:
                        try:
                            start = await self.start_generation_job(
                                session=lesson_session, request=lesson_request
                            )
                            await lesson_session.commit()
                        except Exception:
                            await lesson_session.rollback()
                            raise

                    await self.run_generation_pipeline(start.job_id)

                    async with self._session_factory() as lesson_session:
                        job = await self._job_repo.get(
                            session=lesson_session, job_id=start.job_id
                        )
                        if job.status == AudioGenerationJobStatus.FAILED:
                            raise AudioGenerationException(
                                message=job.error_message or "Audio generation failed"
                            )
                        return AudioGenerationResultDTO(
                            lesson_id=lesson_record.id,
                            job_id=job.id,
                            playlist_url=start.playlist_url,
                            generation_time_seconds=0.0,
                        )
                except Exception as exc:
                    generation_errors.append(
                        GenerationErrorDTO(
                            lesson_id=lesson_record.id,
                            error_type=type(exc).__name__,
                            error_message=str(exc),
                        )
                    )
                    return None

        results = await asyncio.gather(
            *[process_lesson_with_semaphore(lesson) for lesson in ready_lessons]
        )
        generated_results = [result for result in results if result is not None]

        return BatchAudioGenerationResultDTO(
            results=generated_results,
            errors=generation_errors,
            total_requested=len(ready_lessons),
        )
