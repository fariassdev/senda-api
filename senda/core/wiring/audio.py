"""Factory functions for TTS, storage, and voice catalog wiring."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from senda.core.enums import TtsProvider
from senda.core.settings.base import BaseAppSettings
from senda.domain.repositories.course import ICourseRepository
from senda.domain.repositories.lesson import ILessonRepository
from senda.domain.repositories.lesson_audio import ILessonAudioRepository
from senda.domain.repositories.voice import IVoiceRepository
from senda.domain.services.audio_generation import (
    IAudioGenerationService,
    IAudioProvider,
    IStorageProvider,
)
from senda.domain.services.voice import IVoiceService
from senda.domain.services.voice_asset_provisioning import IVoiceAssetProvisioner
from senda.infrastructure.providers.chatterbox_audio_provider import (
    ChatterboxAudioProvider,
)
from senda.infrastructure.providers.chatterbox_modal import ChatterboxModalSettings
from senda.infrastructure.providers.chatterbox_voice_asset_provisioner import (
    ChatterboxVoiceAssetProvisioner,
)
from senda.infrastructure.providers.kokoro_audio_provider import KokoroAudioProvider
from senda.infrastructure.providers.s3_storage_provider import S3StorageProvider
from senda.infrastructure.utils.audio_processor import AudioProcessor
from senda.services.audio_generation import AudioGenerationService
from senda.services.voice import VoiceService


def build_storage_provider(settings: BaseAppSettings) -> IStorageProvider:
    return S3StorageProvider(
        bucket_name=settings.aws_s3_bucket, region=settings.aws_region
    )


def build_kokoro_audio_provider(settings: BaseAppSettings) -> IAudioProvider:
    return KokoroAudioProvider(
        api_url=settings.kokoro_api_url, timeout=settings.kokoro_api_timeout
    )


def _build_chatterbox_modal_settings(
    settings: BaseAppSettings,
) -> ChatterboxModalSettings:
    return ChatterboxModalSettings.from_app_settings(settings)


def _build_chatterbox_stack(
    settings: BaseAppSettings,
) -> tuple[IAudioProvider, IVoiceAssetProvisioner]:
    modal = _build_chatterbox_modal_settings(settings)
    audio_provider = ChatterboxAudioProvider(modal)
    provisioner = ChatterboxVoiceAssetProvisioner(
        modal=modal, audio_provider=audio_provider
    )
    return audio_provider, provisioner


def build_chatterbox_audio_provider(settings: BaseAppSettings) -> IAudioProvider:
    return _build_chatterbox_stack(settings)[0]


def build_audio_providers(
    settings: BaseAppSettings,
) -> dict[TtsProvider, IAudioProvider]:
    return {
        TtsProvider.KOKORO: build_kokoro_audio_provider(settings),
        TtsProvider.CHATTERBOX: build_chatterbox_audio_provider(settings),
    }


def build_voice_asset_provisioners(
    settings: BaseAppSettings,
) -> dict[TtsProvider, IVoiceAssetProvisioner]:
    return {TtsProvider.CHATTERBOX: _build_chatterbox_stack(settings)[1]}


def build_audio_generation_service(
    *,
    settings: BaseAppSettings,
    course_repo: ICourseRepository,
    lesson_repo: ILessonRepository,
    voice_repo: IVoiceRepository,
    session_factory: async_sessionmaker[AsyncSession],
) -> IAudioGenerationService:
    return AudioGenerationService(
        course_repo=course_repo,
        lesson_repo=lesson_repo,
        voice_repo=voice_repo,
        storage_provider=build_storage_provider(settings),
        audio_providers=build_audio_providers(settings),
        session_factory=session_factory,
        audio_processor=AudioProcessor(),
        max_concurrent_lessons=settings.max_concurrent_lessons,
        max_concurrent_tts=settings.max_concurrent_tts,
    )


def build_voice_service(
    *,
    settings: BaseAppSettings,
    voice_repo: IVoiceRepository,
    lesson_audio_repo: ILessonAudioRepository,
) -> IVoiceService:
    return VoiceService(
        voice_repo=voice_repo,
        lesson_audio_repo=lesson_audio_repo,
        storage_provider=build_storage_provider(settings),
        voice_asset_provisioners=build_voice_asset_provisioners(settings),
        audio_processor=AudioProcessor(),
    )
