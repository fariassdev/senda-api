"""
Test suite for audio generation service logic.
Tests business logic without external API calls.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.enums import LessonStatus
from senda.core.exceptions import (
    AudioGenerationException,
    AudioProviderException,
    CourseNotFoundException,
    InvalidLessonStateException,
    LessonNotFoundException,
    StorageProviderException,
)
from senda.domain.dtos.audio_generation import (
    AudioGenerationRequestDTO,
    AudioGenerationResultDTO,
    BatchAudioGenerationResultDTO,
    CourseAudioGenerationRequestDTO,
)
from senda.domain.dtos.course import CourseRecordDTO
from senda.domain.dtos.lesson import LessonRecordDTO
from senda.domain.dtos.script_generation import ScriptPartDTO
from senda.domain.repositories.course import ICourseRepository
from senda.domain.repositories.lesson import ILessonRepository
from senda.domain.repositories.voice import IVoiceRepository
from senda.domain.services.audio_generation import (
    IAudioGenerationService,
    IAudioProvider,
    IStorageProvider,
)
from senda.infrastructure.utils.audio_processor import AudioProcessor
from senda.services.audio_generation import AudioGenerationService


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
        return provider

    @pytest.fixture
    def mock_audio_processor(self) -> Mock:
        """Mock audio processor"""
        processor = Mock(spec=AudioProcessor)

        mock_audio_segment = Mock()
        mock_audio_segment.raw_data = b"fake_audio_data"
        mock_audio_segment.__len__ = Mock(return_value=5000)

        processor.combine_script_parts = Mock(return_value=mock_audio_segment)
        processor.export_to_mp3 = Mock(return_value=b"fake_mp3_data")
        return processor

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
    def audio_service(
        self,
        mock_course_repo,
        mock_lesson_repo,
        mock_voice_repo,
        mock_audio_provider,
        mock_chatterbox_provider,
        mock_storage_provider,
        mock_audio_processor,
    ) -> IAudioGenerationService:
        """Create AudioGenerationService with mocked dependencies"""
        audio_providers = {
            "kokoro": mock_audio_provider,
            "chatterbox": mock_chatterbox_provider,
        }
        return AudioGenerationService(
            course_repo=mock_course_repo,
            lesson_repo=mock_lesson_repo,
            voice_repo=mock_voice_repo,
            storage_provider=mock_storage_provider,
            audio_providers=audio_providers,
            audio_processor=mock_audio_processor,
        )

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Mock database session"""
        return Mock(spec=AsyncSession)

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
            audio_url=None,
            script_generated_at=datetime.now(timezone.utc),
            audio_generated_at=None,
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
        mock_audio_provider,
        mock_storage_provider,
        mock_audio_processor,
    ):
        """Test successful audio generation for a lesson"""
        request = AudioGenerationRequestDTO(lesson_id=1, user_id=1)

        mock_lesson_repo.get_or_none = AsyncMock(return_value=sample_lesson_record)
        mock_course_repo.get_by_id = AsyncMock(return_value=sample_course_record)
        mock_lesson_repo.update = AsyncMock(return_value=sample_lesson_record)

        result = await audio_service.generate_lesson_audio(
            session=mock_session, request=request
        )

        assert isinstance(result, AudioGenerationResultDTO)
        assert result.lesson_id == 1
        assert result.audio_url == "https://s3.amazonaws.com/audio/test.mp3"
        assert result.generation_time_seconds >= 0
        assert result.file_size_bytes == 13

        mock_audio_processor.combine_script_parts.assert_called_once()
        mock_storage_provider.upload_audio.assert_called_once()
        # Two updates: 1) Set AUDIO_GENERATING, 2) Set AUDIO_COMPLETED with audio_url
        assert mock_lesson_repo.update.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_lesson_not_found(
        self, audio_service, mock_session, mock_lesson_repo
    ):
        """Test error when lesson does not exist"""
        request = AudioGenerationRequestDTO(lesson_id=999, user_id=1)
        mock_lesson_repo.get_or_none = AsyncMock(return_value=None)

        with pytest.raises(LessonNotFoundException):
            await audio_service.generate_lesson_audio(
                session=mock_session, request=request
            )

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_invalid_state(
        self, audio_service, mock_session, sample_lesson_record, mock_lesson_repo
    ):
        """Test error when lesson is not in SCRIPT_COMPLETED state"""
        request = AudioGenerationRequestDTO(lesson_id=1, user_id=1)

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
    async def test_generate_lesson_audio_course_not_found(
        self,
        audio_service,
        mock_session,
        sample_lesson_record,
        mock_lesson_repo,
        mock_course_repo,
    ):
        """Test error when course does not exist"""
        request = AudioGenerationRequestDTO(lesson_id=1, user_id=1)

        mock_lesson_repo.get_or_none = AsyncMock(return_value=sample_lesson_record)
        mock_course_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(CourseNotFoundException):
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
    ):
        """Test error when lesson has no script content"""
        request = AudioGenerationRequestDTO(lesson_id=1, user_id=1)

        empty_script_lesson = LessonRecordDTO(
            **{**sample_lesson_record.__dict__, "script": "[]"}
        )

        mock_lesson_repo.get_or_none = AsyncMock(return_value=empty_script_lesson)
        mock_course_repo.get_by_id = AsyncMock(return_value=sample_course_record)
        mock_lesson_repo.update = AsyncMock(return_value=empty_script_lesson)

        with pytest.raises(AudioGenerationException) as exc_info:
            await audio_service.generate_lesson_audio(
                session=mock_session, request=request
            )

        assert "no script content" in str(exc_info.value).lower()

        assert mock_lesson_repo.update.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_provider_fails(
        self,
        audio_service,
        mock_session,
        sample_lesson_record,
        sample_course_record,
        mock_lesson_repo,
        mock_course_repo,
        mock_audio_processor,
    ):
        """Test error handling when TTS provider fails"""
        request = AudioGenerationRequestDTO(lesson_id=1, user_id=1)

        mock_lesson_repo.get_or_none = AsyncMock(return_value=sample_lesson_record)
        mock_course_repo.get_by_id = AsyncMock(return_value=sample_course_record)
        mock_lesson_repo.update = AsyncMock(return_value=sample_lesson_record)

        mock_audio_processor.combine_script_parts.side_effect = AudioProviderException(
            message="TTS service unavailable"
        )

        with pytest.raises(AudioProviderException):
            await audio_service.generate_lesson_audio(
                session=mock_session, request=request
            )

        assert mock_lesson_repo.update.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_lesson_audio_storage_fails(
        self,
        audio_service,
        mock_session,
        sample_lesson_record,
        sample_course_record,
        mock_lesson_repo,
        mock_course_repo,
        mock_storage_provider,
    ):
        """Test error handling when storage upload fails"""
        request = AudioGenerationRequestDTO(lesson_id=1, user_id=1)

        mock_lesson_repo.get_or_none = AsyncMock(return_value=sample_lesson_record)
        mock_course_repo.get_by_id = AsyncMock(return_value=sample_course_record)
        mock_lesson_repo.update = AsyncMock(return_value=sample_lesson_record)

        mock_storage_provider.upload_audio.side_effect = StorageProviderException(
            message="S3 upload failed"
        )

        with pytest.raises(StorageProviderException):
            await audio_service.generate_lesson_audio(
                session=mock_session, request=request
            )

        assert mock_lesson_repo.update.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_course_audios_success(
        self,
        audio_service,
        mock_session,
        sample_course_record,
        mock_course_repo,
        mock_lesson_repo,
    ):
        """Test successful bulk audio generation for course"""
        request = CourseAudioGenerationRequestDTO(user_id=1, slug="test-course")

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
            audio_url=None,
            script_generated_at=datetime.now(timezone.utc),
            audio_generated_at=None,
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
            audio_url=None,
            script_generated_at=datetime.now(timezone.utc),
            audio_generated_at=None,
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

        def mock_generate_lesson_audio(session, request):
            return AudioGenerationResultDTO(
                lesson_id=request.lesson_id,
                audio_url="https://s3.amazonaws.com/audio/test.mp3",
                generation_time_seconds=10.0,
                file_size_bytes=1024,
            )

        audio_service.generate_lesson_audio = AsyncMock(
            side_effect=mock_generate_lesson_audio
        )

        batch_result = await audio_service.generate_course_audios(
            session=mock_session, request=request
        )

        assert isinstance(batch_result, BatchAudioGenerationResultDTO)
        assert len(batch_result.results) == 2
        assert len(batch_result.errors) == 0
        assert batch_result.total_requested == 2
        assert audio_service.generate_lesson_audio.call_count == 2

        # Validate the results contain valid AudioGenerationResultDTO objects
        for result in batch_result.results:
            assert isinstance(result, AudioGenerationResultDTO)
            assert result.lesson_id in [
                1,
                2,
            ]  # Should be lesson 1 or 2, not the pending lesson 3
            assert result.audio_url == "https://s3.amazonaws.com/audio/test.mp3"
            assert result.generation_time_seconds == 10.0
            assert result.file_size_bytes == 1024

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
    ):
        """Test bulk generation when no lessons are ready"""
        request = CourseAudioGenerationRequestDTO(user_id=1, slug="test-course")

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
            audio_url=None,
            script_generated_at=None,
            audio_generated_at=None,
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
    ):
        """Test that bulk generation continues even if individual lessons fail"""
        request = CourseAudioGenerationRequestDTO(user_id=1, slug="test-course")

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
            audio_url=None,
            script_generated_at=datetime.now(timezone.utc),
            audio_generated_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        lesson2 = LessonRecordDTO(**{**lesson1.__dict__, "id": 2})

        mock_course_repo.get_by_slug = AsyncMock(return_value=sample_course_record)
        mock_lesson_repo.list_by_course = AsyncMock(return_value=[lesson1, lesson2])

        call_count = 0

        async def generate_with_failure(session, request):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise AudioProviderException(message="TTS failed")
            return AudioGenerationResultDTO(
                lesson_id=request.lesson_id,
                audio_url="https://s3.amazonaws.com/audio/test.mp3",
                generation_time_seconds=10.0,
                file_size_bytes=1024,
            )

        audio_service.generate_lesson_audio = AsyncMock(
            side_effect=generate_with_failure
        )

        batch_result = await audio_service.generate_course_audios(
            session=mock_session, request=request
        )

        assert isinstance(batch_result, BatchAudioGenerationResultDTO)
        assert len(batch_result.results) == 1
        assert len(batch_result.errors) == 1
        assert batch_result.total_requested == 2

        # Validate the error was captured
        error = batch_result.errors[0]
        assert error.lesson_id == 1
        assert error.error_type == "AudioProviderException"
        assert "TTS failed" in error.error_message

        # Validate the successful result has the second lesson's data
        result = batch_result.results[0]
        assert isinstance(result, AudioGenerationResultDTO)
        assert result.lesson_id == 2
        assert result.audio_url == "https://s3.amazonaws.com/audio/test.mp3"
        assert result.generation_time_seconds == 10.0
        assert result.file_size_bytes == 1024
