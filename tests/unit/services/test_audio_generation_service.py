"""
Test suite for audio generation service logic.
Tests business logic without external API calls.
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.enums import AudioGenerationJobStatus, LessonStatus, TtsProvider
from senda.core.exceptions import (
    AudioGenerationException,
    AudioProviderException,
    AudioVoiceRequiredException,
    InvalidLessonStateException,
    LessonNotFoundException,
    StorageProviderException,
    VoiceNotActiveException,
    VoiceNotFoundException,
)
from senda.domain.dtos.audio_generation import (
    AudioConfigDTO,
    AudioGenerationRequestDTO,
    AudioGenerationResultDTO,
    BatchAudioGenerationResultDTO,
    CourseAudioGenerationRequestDTO,
    StartGenerationJobResultDTO,
)
from senda.domain.dtos.course import CourseRecordDTO
from senda.domain.dtos.lesson import LessonRecordDTO
from senda.domain.dtos.script_generation import ScriptPartDTO
from senda.domain.dtos.voice import GenderEnum, VoiceDTO
from senda.domain.dtos.audio_generation_job import AudioGenerationJobDTO
from senda.domain.dtos.lesson_audio import LessonAudioDTO
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
from senda.infrastructure.audio.composer import AudioComposer, HlsCompositionResult
from senda.infrastructure.utils.audio_processor import AudioProcessor
from senda.services.audio_generation import AudioGenerationService, s3_base_path_for


def make_job_dto(
    *,
    job_id,
    lesson_id: int = 1,
    voice_id,
    status: AudioGenerationJobStatus = AudioGenerationJobStatus.PENDING,
    segment_count: int | None = None,
    duration_ms: int | None = None,
) -> AudioGenerationJobDTO:
    return AudioGenerationJobDTO(
        id=job_id,
        lesson_id=lesson_id,
        voice_id=voice_id,
        voice_slug="af_nicole",
        audio_provider=TtsProvider.KOKORO.value,
        s3_base_path=s3_base_path_for(lesson_id, job_id),
        speed=1.0,
        status=status,
        segments_available=0,
        segment_count=segment_count,
        duration_ms=duration_ms,
        lesson_audio_id=None,
        error_message=None,
        started_at=None,
        completed_at=None,
        created_at=datetime.now(timezone.utc),
    )


class TestAudioGenerationService:
    """Test suite for AudioGenerationService"""

    @pytest.fixture
    def mock_course_repo(self) -> Mock:
        """Mock course repository"""
        return Mock(spec=ICourseRepository)

    @pytest.fixture
    def mock_lesson_repo(self) -> Mock:
        """Mock lesson repository"""
        return Mock(spec=ILessonRepository)

    @pytest.fixture
    def mock_audio_provider(self) -> AsyncMock:
        """Mock audio provider"""
        provider = AsyncMock(spec=IAudioProvider)
        provider.generate_speech = AsyncMock(return_value=b"fake_pcm_data")
        return provider

    @pytest.fixture
    def mock_storage_provider(self) -> AsyncMock:
        """Mock storage provider"""
        provider = AsyncMock(spec=IStorageProvider)
        provider.upload_audio = AsyncMock(
            return_value="https://s3.amazonaws.com/audio/test.mp3"
        )
        provider.public_url_for_key = Mock(
            return_value="https://s3.amazonaws.com/audio/test.mp3"
        )
        return provider

    @pytest.fixture
    def mock_job_repo(self) -> Mock:
        return Mock(spec=IAudioGenerationJobRepository)

    @pytest.fixture
    def mock_lesson_audio_repo(self) -> Mock:
        return Mock(spec=ILessonAudioRepository)

    @pytest.fixture
    def mock_audio_composer(self) -> AsyncMock:
        composer = AsyncMock(spec=AudioComposer)
        composer.compose_hls = AsyncMock(
            return_value=HlsCompositionResult(
                segment_count=2,
                duration_ms=12000,
                playlist_url="https://cdn.test/meditations/1/job/playlist.m3u8",
            )
        )
        return composer

    @pytest.fixture
    def mock_voice_repo(self) -> Mock:
        """Mock voice repository"""
        return Mock(spec=IVoiceRepository)

    @pytest.fixture
    def mock_chatterbox_provider(self) -> AsyncMock:
        """Mock chatterbox provider"""
        provider = AsyncMock(spec=IAudioProvider)
        provider.generate_speech = AsyncMock(return_value=b"fake_pcm_data")
        return provider

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Mock database session"""
        session = Mock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def mock_session_factory(self, mock_session: Mock):
        """Session factory yielding the shared mock session for batch tests."""

        @asynccontextmanager
        async def factory():
            yield mock_session

        return factory

    @pytest.fixture
    def audio_service(
        self,
        mock_course_repo,
        mock_lesson_repo,
        mock_voice_repo,
        mock_job_repo,
        mock_lesson_audio_repo,
        mock_audio_provider,
        mock_chatterbox_provider,
        mock_storage_provider,
        mock_audio_composer,
        mock_session_factory,
    ) -> IAudioGenerationService:
        """Create AudioGenerationService with mocked dependencies"""
        audio_providers = {
            TtsProvider.KOKORO: mock_audio_provider,
            TtsProvider.CHATTERBOX: mock_chatterbox_provider,
        }
        return AudioGenerationService(
            course_repo=mock_course_repo,
            lesson_repo=mock_lesson_repo,
            voice_repo=mock_voice_repo,
            job_repo=mock_job_repo,
            lesson_audio_repo=mock_lesson_audio_repo,
            storage_provider=mock_storage_provider,
            audio_composer=mock_audio_composer,
            audio_providers=audio_providers,
            session_factory=mock_session_factory,
            cdn_base_url="https://cdn.test",
        )

    @pytest.fixture
    def sample_lesson_record(self) -> LessonRecordDTO:
        """Sample lesson record with completed script"""
        return LessonRecordDTO(
            id=1,
            course_id=1,
            lesson_number=1,
            title="Introduction",
            core_practice="Breathing",
            key_point="Focus on breath",
            tone="calm",
            duration_minutes=10,
            status=LessonStatus.SCRIPT_COMPLETED,
            script='[{"type": "speak", "content": "Hello"}]',
            script_generated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_course_record(self) -> CourseRecordDTO:
        """Sample course record"""
        return CourseRecordDTO(
            id=1,
            author_id=1,
            slug="test-course",
            title="Test Course",
            description="Test description",
            difficulty_level="Beginner",
            active=True,
            image_placeholder_url=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def kokoro_voice_id(self):
        return uuid4()

    @pytest.fixture
    def kokoro_catalog_voice(self, kokoro_voice_id) -> VoiceDTO:
        return VoiceDTO(
            id=kokoro_voice_id,
            name="Nicole",
            slug="af_nicole",
            description=None,
            language="en",
            gender=GenderEnum.FEMALE,
            reference_s3_key="voices/reference/af_nicole.wav",
            sample_s3_key="voices/samples/af_nicole.mp3",
            reference_audio_url="https://example.com/ref.wav",
            sample_audio_url="https://example.com/sample.mp3",
            tts_provider=TtsProvider.KOKORO.value,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def audio_config(self, kokoro_voice_id) -> AudioConfigDTO:
        return AudioConfigDTO(voice_id=kokoro_voice_id)

    @pytest.fixture
    def sample_script_parts(self) -> list[ScriptPartDTO]:
        """Sample script parts"""
        from senda.core.enums import ScriptPartType

        return [
            ScriptPartDTO(
                type=ScriptPartType.SPEAK, content="Hello world", duration=None
            ),
            ScriptPartDTO(type=ScriptPartType.PAUSE, content=None, duration=2.0),
        ]

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_success(
        self,
        audio_service,
        mock_session,
        sample_lesson_record,
        sample_course_record,
        mock_lesson_repo,
        mock_course_repo,
        mock_voice_repo,
        kokoro_catalog_voice,
        audio_config,
        mock_audio_provider,
        mock_chatterbox_provider,
        mock_storage_provider,
        mock_job_repo,
        mock_lesson_audio_repo,
        mock_audio_composer,
        kokoro_voice_id,
    ):
        """Test successful HLS audio generation for a lesson"""
        request = AudioGenerationRequestDTO(
            lesson_id=1, user_id=1, audio_config=audio_config
        )
        job_id = uuid4()
        pending_job = make_job_dto(
            job_id=job_id, voice_id=kokoro_voice_id, status=AudioGenerationJobStatus.PENDING
        )
        completed_job = make_job_dto(
            job_id=job_id,
            voice_id=kokoro_voice_id,
            status=AudioGenerationJobStatus.COMPLETED,
            segment_count=2,
            duration_ms=12000,
        )

        mock_lesson_repo.get_or_none = AsyncMock(return_value=sample_lesson_record)
        mock_lesson_repo.get = AsyncMock(return_value=sample_lesson_record)
        mock_lesson_repo.update = AsyncMock(return_value=sample_lesson_record)
        mock_voice_repo.get_or_none = AsyncMock(return_value=kokoro_catalog_voice)
        mock_job_repo.get_active_for_lesson_voice = AsyncMock(return_value=None)
        mock_job_repo.add = AsyncMock(return_value=pending_job)
        mock_job_repo.get = AsyncMock(return_value=completed_job)
        mock_lesson_audio_repo.upsert = AsyncMock(
            return_value=LessonAudioDTO(
                id=uuid4(),
                lesson_id=1,
                voice_id=kokoro_voice_id,
                voice_slug="af_nicole",
                audio_provider=TtsProvider.KOKORO.value,
                playlist_url="https://cdn.test/meditations/1/job/playlist.m3u8",
                hls_base_path=s3_base_path_for(1, job_id),
                segment_count=2,
                duration_ms=12000,
                generated_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )

        result = await audio_service.generate_lesson_audio(
            session=mock_session, request=request
        )

        assert isinstance(result, AudioGenerationResultDTO)
        assert result.lesson_id == 1
        assert result.playlist_url.endswith("playlist.m3u8")
        assert result.segment_count == 2
        assert result.duration_ms == 12000
        assert result.generation_time_seconds >= 0

        mock_audio_composer.compose_hls.assert_called_once()
        mock_audio_provider.generate_speech.assert_called()
        mock_chatterbox_provider.generate_speech.assert_not_called()
        assert mock_lesson_repo.update.call_count >= 2

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_uses_catalog_voice_provider(
        self,
        audio_service,
        mock_session,
        sample_lesson_record,
        sample_course_record,
        mock_lesson_repo,
        mock_course_repo,
        mock_voice_repo,
        mock_chatterbox_provider,
        mock_audio_provider,
    ):
        """audio_config.voice_id selects provider and slug from the voices catalog."""
        voice_id = uuid4()
        catalog_voice = VoiceDTO(
            id=voice_id,
            name="Lucy",
            slug="Lucy",
            description=None,
            language="en",
            gender=GenderEnum.FEMALE,
            reference_s3_key="voices/reference/Lucy.wav",
            sample_s3_key="voices/samples/Lucy.mp3",
            reference_audio_url="https://example.com/ref.wav",
            sample_audio_url="https://example.com/sample.mp3",
            tts_provider=TtsProvider.CHATTERBOX.value,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        job_id = uuid4()
        mock_lesson_repo.get_or_none = AsyncMock(return_value=sample_lesson_record)
        mock_lesson_repo.get = AsyncMock(return_value=sample_lesson_record)
        mock_lesson_repo.update = AsyncMock(return_value=sample_lesson_record)
        mock_voice_repo.get_or_none = AsyncMock(return_value=catalog_voice)
        mock_job_repo = audio_service._job_repo
        mock_job_repo.get_active_for_lesson_voice = AsyncMock(return_value=None)
        mock_job_repo.add = AsyncMock(
            return_value=make_job_dto(job_id=job_id, voice_id=voice_id)
        )
        mock_job_repo.get = AsyncMock(
            return_value=make_job_dto(
                job_id=job_id,
                voice_id=voice_id,
                status=AudioGenerationJobStatus.COMPLETED,
                segment_count=1,
                duration_ms=6000,
            )
        )
        audio_service._lesson_audio_repo.upsert = AsyncMock(
            return_value=LessonAudioDTO(
                id=uuid4(),
                lesson_id=1,
                voice_id=voice_id,
                voice_slug="Lucy",
                audio_provider=TtsProvider.CHATTERBOX.value,
                playlist_url="https://cdn.test/playlist.m3u8",
                hls_base_path=s3_base_path_for(1, job_id),
                segment_count=1,
                duration_ms=6000,
                generated_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )

        await audio_service.generate_lesson_audio(
            session=mock_session,
            request=AudioGenerationRequestDTO(
                lesson_id=1, user_id=1, audio_config=AudioConfigDTO(voice_id=voice_id)
            ),
        )

        mock_chatterbox_provider.generate_speech.assert_called()
        mock_audio_provider.generate_speech.assert_not_called()
        mock_chatterbox_provider.generate_speech.assert_called_with(
            text="Hello", voice="Lucy", speed=1.0
        )

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_requires_catalog_voice(
        self,
        audio_service,
        mock_session,
        sample_lesson_record,
        sample_course_record,
        mock_lesson_repo,
        mock_course_repo,
        mock_voice_repo,
        audio_config,
    ):
        """Missing or unknown catalog voice fails before TTS."""
        mock_lesson_repo.get_or_none = AsyncMock(return_value=sample_lesson_record)
        mock_course_repo.get_by_id = AsyncMock(return_value=sample_course_record)
        mock_voice_repo.get_or_none = AsyncMock(return_value=None)

        with pytest.raises(VoiceNotFoundException):
            await audio_service.generate_lesson_audio(
                session=mock_session,
                request=AudioGenerationRequestDTO(
                    lesson_id=1, user_id=1, audio_config=audio_config
                ),
            )

        mock_lesson_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_rejects_inactive_voice(
        self,
        audio_service,
        mock_session,
        sample_lesson_record,
        sample_course_record,
        mock_lesson_repo,
        mock_course_repo,
        mock_voice_repo,
        kokoro_catalog_voice,
        audio_config,
    ):
        inactive_voice = VoiceDTO(
            **{**kokoro_catalog_voice.__dict__, "is_active": False}
        )
        mock_lesson_repo.get_or_none = AsyncMock(return_value=sample_lesson_record)
        mock_course_repo.get_by_id = AsyncMock(return_value=sample_course_record)
        mock_voice_repo.get_or_none = AsyncMock(return_value=inactive_voice)

        with pytest.raises(VoiceNotActiveException):
            await audio_service.generate_lesson_audio(
                session=mock_session,
                request=AudioGenerationRequestDTO(
                    lesson_id=1, user_id=1, audio_config=audio_config
                ),
            )

        mock_lesson_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_lesson_not_found(
        self, audio_service, mock_session, mock_lesson_repo, audio_config
    ):
        """Test error when lesson does not exist"""
        request = AudioGenerationRequestDTO(
            lesson_id=999, user_id=1, audio_config=audio_config
        )
        mock_lesson_repo.get_or_none = AsyncMock(return_value=None)

        with pytest.raises(LessonNotFoundException):
            await audio_service.generate_lesson_audio(
                session=mock_session, request=request
            )

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_invalid_state(
        self,
        audio_service,
        mock_session,
        sample_lesson_record,
        mock_lesson_repo,
        audio_config,
    ):
        """Test error when lesson is not in SCRIPT_COMPLETED state"""
        request = AudioGenerationRequestDTO(
            lesson_id=1, user_id=1, audio_config=audio_config
        )

        pending_lesson = sample_lesson_record
        pending_lesson = LessonRecordDTO(
            **{**pending_lesson.__dict__, "status": LessonStatus.PENDING}
        )

        mock_lesson_repo.get_or_none = AsyncMock(return_value=pending_lesson)

        with pytest.raises(InvalidLessonStateException):
            await audio_service.generate_lesson_audio(
                session=mock_session, request=request
            )

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_empty_script(
        self,
        audio_service,
        mock_session,
        sample_lesson_record,
        sample_course_record,
        mock_lesson_repo,
        mock_course_repo,
        mock_voice_repo,
        kokoro_catalog_voice,
        audio_config,
    ):
        """Test error when lesson has no script content"""
        request = AudioGenerationRequestDTO(
            lesson_id=1, user_id=1, audio_config=audio_config
        )

        empty_script_lesson = LessonRecordDTO(
            **{**sample_lesson_record.__dict__, "script": "[]"}
        )

        mock_lesson_repo.get_or_none = AsyncMock(return_value=empty_script_lesson)
        mock_course_repo.get_by_id = AsyncMock(return_value=sample_course_record)
        mock_lesson_repo.update = AsyncMock(return_value=empty_script_lesson)
        mock_voice_repo.get_or_none = AsyncMock(return_value=kokoro_catalog_voice)

        with pytest.raises(AudioGenerationException) as exc_info:
            await audio_service.generate_lesson_audio(
                session=mock_session, request=request
            )

        assert "no script content" in str(exc_info.value).lower()

        mock_lesson_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_provider_fails(
        self,
        audio_service,
        mock_session,
        sample_lesson_record,
        sample_course_record,
        mock_lesson_repo,
        mock_course_repo,
        mock_voice_repo,
        kokoro_catalog_voice,
        audio_config,
        mock_job_repo,
        mock_audio_composer,
        kokoro_voice_id,
    ):
        """Test error handling when HLS composition fails"""
        request = AudioGenerationRequestDTO(
            lesson_id=1, user_id=1, audio_config=audio_config
        )
        job_id = uuid4()
        mock_lesson_repo.get_or_none = AsyncMock(return_value=sample_lesson_record)
        mock_lesson_repo.get = AsyncMock(return_value=sample_lesson_record)
        mock_lesson_repo.update = AsyncMock(return_value=sample_lesson_record)
        mock_voice_repo.get_or_none = AsyncMock(return_value=kokoro_catalog_voice)
        mock_job_repo.get_active_for_lesson_voice = AsyncMock(return_value=None)
        mock_job_repo.add = AsyncMock(
            return_value=make_job_dto(job_id=job_id, voice_id=kokoro_voice_id)
        )
        mock_job_repo.get = AsyncMock(
            return_value=make_job_dto(
                job_id=job_id,
                voice_id=kokoro_voice_id,
                status=AudioGenerationJobStatus.FAILED,
            )
        )
        mock_audio_composer.compose_hls.side_effect = StorageProviderException(
            message="S3 upload failed"
        )

        with pytest.raises(AudioGenerationException):
            await audio_service.generate_lesson_audio(
                session=mock_session, request=request
            )

        assert mock_lesson_repo.update.call_count >= 2

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_storage_fails(
        self,
        audio_service,
        mock_session,
        sample_lesson_record,
        sample_course_record,
        mock_lesson_repo,
        mock_course_repo,
        mock_voice_repo,
        kokoro_catalog_voice,
        audio_config,
        mock_job_repo,
        mock_audio_composer,
        kokoro_voice_id,
    ):
        """Test pipeline marks lesson failed when composition raises"""
        request = AudioGenerationRequestDTO(
            lesson_id=1, user_id=1, audio_config=audio_config
        )
        job_id = uuid4()
        mock_lesson_repo.get_or_none = AsyncMock(return_value=sample_lesson_record)
        mock_lesson_repo.get = AsyncMock(return_value=sample_lesson_record)
        mock_lesson_repo.update = AsyncMock(return_value=sample_lesson_record)
        mock_voice_repo.get_or_none = AsyncMock(return_value=kokoro_catalog_voice)
        mock_job_repo.get_active_for_lesson_voice = AsyncMock(return_value=None)
        mock_job_repo.add = AsyncMock(
            return_value=make_job_dto(job_id=job_id, voice_id=kokoro_voice_id)
        )
        failed_job = AudioGenerationJobDTO(
            id=job_id,
            lesson_id=1,
            voice_id=kokoro_voice_id,
            voice_slug="af_nicole",
            audio_provider=TtsProvider.KOKORO.value,
            s3_base_path=s3_base_path_for(1, job_id),
            speed=1.0,
            status=AudioGenerationJobStatus.FAILED,
            segments_available=0,
            segment_count=None,
            duration_ms=None,
            lesson_audio_id=None,
            error_message="compose failed",
            started_at=None,
            completed_at=None,
            created_at=datetime.now(timezone.utc),
        )
        mock_job_repo.get = AsyncMock(return_value=failed_job)
        mock_audio_composer.compose_hls.side_effect = AudioGenerationException(
            message="compose failed"
        )

        with pytest.raises(AudioGenerationException):
            await audio_service.generate_lesson_audio(
                session=mock_session, request=request
            )

    @pytest.mark.asyncio
    async def test_generate_course_audios_success(
        self,
        audio_service,
        mock_session,
        sample_course_record,
        mock_course_repo,
        mock_lesson_repo,
        audio_config,
    ):
        """Test successful bulk audio generation for course"""
        request = CourseAudioGenerationRequestDTO(
            user_id=1, slug="test-course", audio_config=audio_config
        )

        lesson1 = LessonRecordDTO(
            id=1,
            course_id=1,
            lesson_number=1,
            title="Lesson 1",
            core_practice="Practice",
            key_point="Point",
            tone="calm",
            duration_minutes=10,
            status=LessonStatus.SCRIPT_COMPLETED,
            script='[{"type": "speak", "content": "Hello"}]',
            script_generated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        lesson2 = LessonRecordDTO(
            id=2,
            course_id=1,
            lesson_number=2,
            title="Lesson 2",
            core_practice="Practice",
            key_point="Point",
            tone="calm",
            duration_minutes=10,
            status=LessonStatus.SCRIPT_COMPLETED,
            script='[{"type": "speak", "content": "World"}]',
            script_generated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        pending_lesson = LessonRecordDTO(
            **{**lesson1.__dict__, "id": 3, "status": LessonStatus.PENDING}
        )

        mock_course_repo.get_by_slug = AsyncMock(return_value=sample_course_record)
        mock_lesson_repo.list_by_course = AsyncMock(
            return_value=[lesson1, lesson2, pending_lesson]
        )

        job_id = uuid4()

        async def mock_start_generation_job(session, request):
            return StartGenerationJobResultDTO(
                job_id=job_id,
                lesson_id=request.lesson_id,
                status=AudioGenerationJobStatus.PENDING,
                playlist_url="https://cdn.test/meditations/playlist.m3u8",
                segments_available=0,
            )

        completed_job = make_job_dto(
            job_id=job_id,
            voice_id=uuid4(),
            status=AudioGenerationJobStatus.COMPLETED,
            segment_count=2,
            duration_ms=1024,
        )
        audio_service._job_repo.get = AsyncMock(return_value=completed_job)
        audio_service.start_generation_job = AsyncMock(side_effect=mock_start_generation_job)
        audio_service.run_generation_pipeline = AsyncMock()

        batch_result = await audio_service.generate_course_audios(
            session=mock_session, request=request
        )

        assert isinstance(batch_result, BatchAudioGenerationResultDTO)
        assert len(batch_result.results) == 2
        assert len(batch_result.errors) == 0
        assert batch_result.total_requested == 2
        assert audio_service.start_generation_job.call_count == 2

        # Validate the results contain valid AudioGenerationResultDTO objects
        for result in batch_result.results:
            assert isinstance(result, AudioGenerationResultDTO)
            assert result.lesson_id in [
                1,
                2,
            ]  # Should be lesson 1 or 2, not the pending lesson 3
            assert result.playlist_url.endswith("playlist.m3u8")
            assert result.duration_ms == 1024

        # Ensure we have results for both ready lessons
        lesson_ids = {result.lesson_id for result in batch_result.results}
        assert lesson_ids == {1, 2}

    @pytest.mark.asyncio
    async def test_generate_course_audios_no_ready_lessons(
        self,
        audio_service,
        mock_session,
        sample_course_record,
        mock_course_repo,
        mock_lesson_repo,
        audio_config,
    ):
        """Test bulk generation when no lessons are ready"""
        request = CourseAudioGenerationRequestDTO(
            user_id=1, slug="test-course", audio_config=audio_config
        )

        pending_lesson = LessonRecordDTO(
            id=1,
            course_id=1,
            lesson_number=1,
            title="Lesson 1",
            core_practice="Practice",
            key_point="Point",
            tone="calm",
            duration_minutes=10,
            status=LessonStatus.PENDING,
            script=None,
            script_generated_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        mock_course_repo.get_by_slug = AsyncMock(return_value=sample_course_record)
        mock_lesson_repo.list_by_course = AsyncMock(return_value=[pending_lesson])

        batch_result = await audio_service.generate_course_audios(
            session=mock_session, request=request
        )

        assert isinstance(batch_result, BatchAudioGenerationResultDTO)
        assert len(batch_result.results) == 0
        assert len(batch_result.errors) == 0
        assert batch_result.total_requested == 0

    @pytest.mark.asyncio
    async def test_generate_course_audios_continues_on_failure(
        self,
        audio_service,
        mock_session,
        sample_course_record,
        mock_course_repo,
        mock_lesson_repo,
        audio_config,
    ):
        """Test that bulk generation continues even if individual lessons fail"""
        request = CourseAudioGenerationRequestDTO(
            user_id=1, slug="test-course", audio_config=audio_config
        )

        lesson1 = LessonRecordDTO(
            id=1,
            course_id=1,
            lesson_number=1,
            title="Lesson 1",
            core_practice="Practice",
            key_point="Point",
            tone="calm",
            duration_minutes=10,
            status=LessonStatus.SCRIPT_COMPLETED,
            script='[{"type": "speak", "content": "Hello"}]',
            script_generated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        lesson2 = LessonRecordDTO(**{**lesson1.__dict__, "id": 2})

        mock_course_repo.get_by_slug = AsyncMock(return_value=sample_course_record)
        mock_lesson_repo.list_by_course = AsyncMock(return_value=[lesson1, lesson2])

        job_id = uuid4()
        call_count = 0

        async def mock_start_generation_job(session, request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise AudioProviderException(message="TTS failed")
            return StartGenerationJobResultDTO(
                job_id=job_id,
                lesson_id=request.lesson_id,
                status=AudioGenerationJobStatus.PENDING,
                playlist_url="https://cdn.test/meditations/playlist.m3u8",
                segments_available=0,
            )

        completed_job = make_job_dto(
            job_id=job_id,
            voice_id=uuid4(),
            lesson_id=2,
            status=AudioGenerationJobStatus.COMPLETED,
            segment_count=2,
            duration_ms=1024,
        )
        audio_service._job_repo.get = AsyncMock(return_value=completed_job)
        audio_service.start_generation_job = AsyncMock(side_effect=mock_start_generation_job)
        audio_service.run_generation_pipeline = AsyncMock()

        batch_result = await audio_service.generate_course_audios(
            session=mock_session, request=request
        )

        assert isinstance(batch_result, BatchAudioGenerationResultDTO)
        assert len(batch_result.results) == 1
        assert len(batch_result.errors) == 1
        assert batch_result.total_requested == 2

        error = batch_result.errors[0]
        assert error.lesson_id == 1
        assert error.error_type == "AudioProviderException"
        assert "TTS failed" in error.error_message

        # Validate the successful result has the second lesson's data
        result = batch_result.results[0]
        assert isinstance(result, AudioGenerationResultDTO)
        assert result.lesson_id == 2
        assert result.playlist_url.endswith("playlist.m3u8")
        assert result.duration_ms == 1024
