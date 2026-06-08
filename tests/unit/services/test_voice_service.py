"""Tests for atomic voice creation via POST /voices pipeline."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from senda.core.enums import TtsProvider, UserRole
from senda.core.exceptions import (
    AudioProviderException,
    StorageProviderException,
    UnsupportedVoiceTtsProviderException,
    VoiceInUseException,
    VoiceNotFoundException,
    VoiceSlugAlreadyExistsException,
)
from senda.domain.dtos.user import UserDTO
from senda.domain.dtos.voice import CreateVoiceDTO, GenderEnum, VoiceDTO
from senda.domain.repositories.lesson_audio import ILessonAudioRepository
from senda.domain.repositories.voice import IVoiceRepository
from senda.domain.services.audio_generation import IStorageProvider
from senda.domain.services.voice_asset_provisioning import IVoiceAssetProvisioner
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
def mock_lesson_audio_repo() -> Mock:
    repo = Mock(spec=ILessonAudioRepository)
    repo.count_using_voice = AsyncMock(return_value=0)
    return repo


@pytest.fixture
def mock_voice_asset_provisioner() -> AsyncMock:
    provisioner = AsyncMock(spec=IVoiceAssetProvisioner)
    provisioner.sync_reference_voice = AsyncMock()
    provisioner.generate_preview_speech = AsyncMock(return_value=b"pcm")
    provisioner.delete_remote_assets = AsyncMock()
    return provisioner


@pytest.fixture
def mock_storage() -> AsyncMock:
    provider = AsyncMock(spec=IStorageProvider)
    provider.upload_file = AsyncMock(return_value="https://bucket.s3.amazonaws.com/key")
    provider.delete_file = AsyncMock()
    provider.public_url_for_key = Mock(
        return_value="https://bucket.s3.amazonaws.com/key"
    )
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
    mock_lesson_audio_repo: Mock,
    mock_storage: AsyncMock,
    mock_voice_asset_provisioner: AsyncMock,
    mock_audio_processor: Mock,
) -> VoiceService:
    return VoiceService(
        voice_repo=mock_voice_repo,
        lesson_audio_repo=mock_lesson_audio_repo,
        storage_provider=mock_storage,
        voice_asset_provisioners={TtsProvider.CHATTERBOX: mock_voice_asset_provisioner},
        audio_processor=mock_audio_processor,
    )


@pytest.fixture
def voice_dto() -> VoiceDTO:
    return VoiceDTO(
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


class TestVoiceServiceCreate:
    @pytest.mark.asyncio
    async def test_create_runs_provisioning_before_db_insert(
        self,
        voice_service: VoiceService,
        mock_voice_repo: Mock,
        mock_voice_asset_provisioner: AsyncMock,
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

        mock_voice_asset_provisioner.sync_reference_voice.side_effect = track_modal
        mock_voice_asset_provisioner.generate_preview_speech.side_effect = track_tts
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
        mock_voice_asset_provisioner: AsyncMock,
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

        mock_voice_asset_provisioner.sync_reference_voice.assert_not_called()
        mock_voice_repo.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_rejects_non_chatterbox_tts_provider(
        self,
        voice_service: VoiceService,
        mock_voice_repo: Mock,
        mock_voice_asset_provisioner: AsyncMock,
        create_dto: CreateVoiceDTO,
        admin_user: UserDTO,
    ) -> None:
        kokoro_dto = CreateVoiceDTO(
            name=create_dto.name,
            slug=create_dto.slug,
            description=create_dto.description,
            language=create_dto.language,
            gender=create_dto.gender,
            tts_provider="kokoro",
        )

        with pytest.raises(UnsupportedVoiceTtsProviderException):
            await voice_service.create_voice(
                session=Mock(),
                create_item=kokoro_dto,
                reference_wav=b"wav",
                current_user=admin_user,
            )

        mock_voice_asset_provisioner.sync_reference_voice.assert_not_called()
        mock_voice_repo.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_does_not_insert_when_modal_fails(
        self,
        voice_service: VoiceService,
        mock_voice_repo: Mock,
        mock_voice_asset_provisioner: AsyncMock,
        create_dto: CreateVoiceDTO,
        admin_user: UserDTO,
    ) -> None:
        mock_voice_asset_provisioner.sync_reference_voice.side_effect = (
            AudioProviderException()
        )

        with pytest.raises(AudioProviderException):
            await voice_service.create_voice(
                session=Mock(),
                create_item=create_dto,
                reference_wav=b"wav",
                current_user=admin_user,
            )

        mock_voice_repo.add.assert_not_called()


class TestVoiceServiceDelete:
    @pytest.mark.asyncio
    async def test_delete_removes_modal_s3_then_db(
        self,
        voice_service: VoiceService,
        mock_voice_repo: Mock,
        mock_lesson_audio_repo: Mock,
        mock_voice_asset_provisioner: AsyncMock,
        mock_storage: AsyncMock,
        voice_dto: VoiceDTO,
        admin_user: UserDTO,
    ) -> None:
        mock_voice_repo.get = AsyncMock(return_value=voice_dto)
        mock_voice_repo.delete = AsyncMock()
        mock_lesson_audio_repo.count_using_voice = AsyncMock(return_value=0)
        call_order: list[str] = []

        async def track_modal(*_args, **_kwargs) -> None:
            call_order.append("modal_delete")

        async def track_s3_delete(key: str, *_args, **_kwargs) -> None:
            call_order.append(f"s3:{key}")

        async def track_db_delete(*_args, **_kwargs) -> None:
            call_order.append("db_delete")

        mock_voice_asset_provisioner.delete_remote_assets.side_effect = track_modal
        mock_storage.delete_file.side_effect = track_s3_delete
        mock_voice_repo.delete.side_effect = track_db_delete

        await voice_service.delete_voice(
            session=Mock(), voice_id=voice_dto.id, current_user=admin_user
        )

        assert call_order == [
            "modal_delete",
            f"s3:{voice_dto.reference_s3_key}",
            f"s3:{voice_dto.sample_s3_key}",
            "db_delete",
        ]

    @pytest.mark.asyncio
    async def test_delete_skips_modal_for_non_chatterbox_provider(
        self,
        voice_service: VoiceService,
        mock_voice_repo: Mock,
        mock_voice_asset_provisioner: AsyncMock,
        voice_dto: VoiceDTO,
        admin_user: UserDTO,
    ) -> None:
        kokoro_voice = VoiceDTO(
            id=voice_dto.id,
            name=voice_dto.name,
            slug=voice_dto.slug,
            description=voice_dto.description,
            language=voice_dto.language,
            gender=voice_dto.gender,
            reference_s3_key=voice_dto.reference_s3_key,
            sample_s3_key=voice_dto.sample_s3_key,
            reference_audio_url=voice_dto.reference_audio_url,
            sample_audio_url=voice_dto.sample_audio_url,
            tts_provider="kokoro",
            is_active=voice_dto.is_active,
            created_at=voice_dto.created_at,
            updated_at=voice_dto.updated_at,
        )
        mock_voice_repo.get = AsyncMock(return_value=kokoro_voice)

        await voice_service.delete_voice(
            session=Mock(), voice_id=kokoro_voice.id, current_user=admin_user
        )

        mock_voice_asset_provisioner.delete_remote_assets.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_raises_when_voice_in_use_by_lessons(
        self,
        voice_service: VoiceService,
        mock_voice_repo: Mock,
        mock_lesson_audio_repo: Mock,
        mock_voice_asset_provisioner: AsyncMock,
        voice_dto: VoiceDTO,
        admin_user: UserDTO,
    ) -> None:
        mock_voice_repo.get = AsyncMock(return_value=voice_dto)
        mock_lesson_audio_repo.count_using_voice = AsyncMock(return_value=2)

        with pytest.raises(VoiceInUseException):
            await voice_service.delete_voice(
                session=Mock(), voice_id=voice_dto.id, current_user=admin_user
            )

        mock_voice_asset_provisioner.delete_remote_assets.assert_not_called()
        mock_voice_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_does_not_remove_db_row_when_s3_fails(
        self,
        voice_service: VoiceService,
        mock_voice_repo: Mock,
        mock_lesson_audio_repo: Mock,
        mock_voice_asset_provisioner: AsyncMock,
        mock_storage: AsyncMock,
        voice_dto: VoiceDTO,
        admin_user: UserDTO,
    ) -> None:
        mock_voice_repo.get = AsyncMock(return_value=voice_dto)
        mock_lesson_audio_repo.count_using_voice = AsyncMock(return_value=0)

        async def fail_on_reference_delete(key: str, *_args, **_kwargs) -> None:
            if key == voice_dto.reference_s3_key:
                raise StorageProviderException(message="S3 delete failed")

        mock_storage.delete_file.side_effect = fail_on_reference_delete

        with pytest.raises(StorageProviderException):
            await voice_service.delete_voice(
                session=Mock(), voice_id=voice_dto.id, current_user=admin_user
            )

        mock_voice_asset_provisioner.delete_remote_assets.assert_called_once_with(
            voice_dto.slug
        )
        mock_voice_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_raises_when_voice_not_found(
        self,
        voice_service: VoiceService,
        mock_voice_repo: Mock,
        mock_voice_asset_provisioner: AsyncMock,
        admin_user: UserDTO,
    ) -> None:
        mock_voice_repo.get = AsyncMock(side_effect=VoiceNotFoundException())

        with pytest.raises(VoiceNotFoundException):
            await voice_service.delete_voice(
                session=Mock(), voice_id=uuid4(), current_user=admin_user
            )

        mock_voice_asset_provisioner.delete_remote_assets.assert_not_called()
        mock_voice_repo.delete.assert_not_called()
