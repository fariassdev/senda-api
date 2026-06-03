"""Tests for atomic voice creation via POST /voices pipeline."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from senda.core.enums import UserRole
from senda.core.exceptions import (
    AudioProviderException,
    VoiceSlugAlreadyExistsException,
)
from senda.domain.dtos.user import UserDTO
from senda.domain.dtos.voice import CreateVoiceDTO, GenderEnum, VoiceDTO
from senda.domain.repositories.voice import IVoiceRepository
from senda.domain.services.audio_generation import IStorageProvider
from senda.infrastructure.utils.audio_processor import AudioProcessor
from senda.services.voice import VoiceService
from senda.services.voice_provisioning import reference_s3_key, sample_s3_key


@pytest.fixture
def admin_user() -> UserDTO:
    dto = UserDTO(
        username="admin",
        email="admin@example.com",
        password_hash="hash",
        bio=None,
        image_url=None,
        name="Admin",
        role=UserRole.ADMIN,
        created_at=datetime.now(),
    )
    dto.id = 1
    return dto


@pytest.fixture
def create_dto() -> CreateVoiceDTO:
    return CreateVoiceDTO(
        name="Test Voice",
        slug="test-voice",
        description=None,
        language="es",
        gender=GenderEnum.NEUTRAL,
        tts_provider="chatterbox",
    )


@pytest.fixture
def mock_voice_repo() -> Mock:
    repo = Mock(spec=IVoiceRepository)
    repo.get_by_slug_or_none = AsyncMock(return_value=None)
    repo.add = AsyncMock(
        return_value=VoiceDTO(
            id=uuid4(),
            name="Test Voice",
            slug="test-voice",
            description=None,
            language="es",
            gender=GenderEnum.NEUTRAL,
            reference_s3_key=reference_s3_key("test-voice"),
            sample_s3_key=sample_s3_key("test-voice"),
            reference_audio_url="https://bucket.s3.amazonaws.com/ref.wav",
            sample_audio_url="https://bucket.s3.amazonaws.com/sample.mp3",
            tts_provider="chatterbox",
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
    )
    return repo


@pytest.fixture
def mock_chatterbox() -> AsyncMock:
    provider = AsyncMock()
    provider.sync_voice_to_volume = AsyncMock()
    provider.generate_speech = AsyncMock(return_value=b"pcm")
    return provider


@pytest.fixture
def mock_storage() -> AsyncMock:
    provider = AsyncMock(spec=IStorageProvider)
    provider.upload_file = AsyncMock(return_value="https://bucket.s3.amazonaws.com/key")
    return provider


@pytest.fixture
def mock_audio_processor() -> Mock:
    processor = Mock(spec=AudioProcessor)
    processor.pcm_to_audio_segment = Mock(return_value=Mock())
    processor.export_to_mp3 = Mock(return_value=b"mp3")
    return processor


@pytest.fixture
def voice_service(
    mock_voice_repo: Mock,
    mock_storage: AsyncMock,
    mock_chatterbox: AsyncMock,
    mock_audio_processor: Mock,
) -> VoiceService:
    return VoiceService(
        voice_repo=mock_voice_repo,
        storage_provider=mock_storage,
        chatterbox_provider=mock_chatterbox,
        audio_processor=mock_audio_processor,
    )


class TestVoiceServiceCreate:
    @pytest.mark.asyncio
    async def test_create_runs_provisioning_before_db_insert(
        self,
        voice_service: VoiceService,
        mock_voice_repo: Mock,
        mock_chatterbox: AsyncMock,
        mock_storage: AsyncMock,
        create_dto: CreateVoiceDTO,
        admin_user: UserDTO,
    ) -> None:
        call_order: list[str] = []

        async def track_modal(*_args, **_kwargs) -> None:
            call_order.append("modal_sync")

        async def track_tts(*_args, **_kwargs) -> bytes:
            call_order.append("tts")
            return b"pcm"

        async def track_upload(*_args, **kwargs) -> str:
            call_order.append(f"s3:{kwargs['key']}")
            return "https://example.com/x"

        async def track_add(*_args, **_kwargs) -> VoiceDTO:
            call_order.append("db_insert")
            return VoiceDTO(
                id=uuid4(),
                name=create_dto.name,
                slug=create_dto.slug,
                description=None,
                language="es",
                gender=GenderEnum.NEUTRAL,
                reference_s3_key=reference_s3_key(create_dto.slug),
                sample_s3_key=sample_s3_key(create_dto.slug),
                reference_audio_url="https://bucket.s3.amazonaws.com/ref.wav",
                sample_audio_url="https://bucket.s3.amazonaws.com/sample.mp3",
                tts_provider="chatterbox",
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

        mock_chatterbox.sync_voice_to_volume.side_effect = track_modal
        mock_chatterbox.generate_speech.side_effect = track_tts
        mock_storage.upload_file.side_effect = track_upload
        mock_voice_repo.add.side_effect = track_add

        await voice_service.create_voice(
            session=Mock(),
            create_item=create_dto,
            reference_wav=b"wav",
            current_user=admin_user,
        )

        assert call_order == [
            "modal_sync",
            "tts",
            f"s3:{reference_s3_key('test-voice')}",
            f"s3:{sample_s3_key('test-voice')}",
            "db_insert",
        ]

    @pytest.mark.asyncio
    async def test_create_raises_when_slug_exists_without_provisioning(
        self,
        voice_service: VoiceService,
        mock_voice_repo: Mock,
        mock_chatterbox: AsyncMock,
        create_dto: CreateVoiceDTO,
        admin_user: UserDTO,
    ) -> None:
        mock_voice_repo.get_by_slug_or_none = AsyncMock(return_value=Mock())

        with pytest.raises(VoiceSlugAlreadyExistsException):
            await voice_service.create_voice(
                session=Mock(),
                create_item=create_dto,
                reference_wav=b"wav",
                current_user=admin_user,
            )

        mock_chatterbox.sync_voice_to_volume.assert_not_called()
        mock_voice_repo.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_does_not_insert_when_modal_fails(
        self,
        voice_service: VoiceService,
        mock_voice_repo: Mock,
        mock_chatterbox: AsyncMock,
        create_dto: CreateVoiceDTO,
        admin_user: UserDTO,
    ) -> None:
        mock_chatterbox.sync_voice_to_volume.side_effect = AudioProviderException()

        with pytest.raises(AudioProviderException):
            await voice_service.create_voice(
                session=Mock(),
                create_item=create_dto,
                reference_wav=b"wav",
                current_user=admin_user,
            )

        mock_voice_repo.add.assert_not_called()
