import logging
from typing import Any
from uuid import UUID

from senda.core.enums import TtsProvider
from senda.core.exceptions import (
    UnsupportedVoiceTtsProviderException,
    VoiceInUseException,
    VoiceSlugAlreadyExistsException,
)
from senda.domain.dtos.user import UserDTO
from senda.domain.dtos.voice import CreateVoiceDTO, UpdateVoiceDTO, VoiceDTO
from senda.domain.repositories.lesson import ILessonRepository
from senda.domain.repositories.voice import IVoiceRepository
from senda.domain.services.audio_generation import IStorageProvider
from senda.domain.services.voice import IVoiceService
from senda.domain.services.voice_asset_provisioning import IVoiceAssetProvisioner
from senda.infrastructure.utils.audio_processor import AudioProcessor
from senda.services.voice_provisioning import provision_voice_assets

logger = logging.getLogger(__name__)


class VoiceService(IVoiceService):
    """Business logic service for managing the Senda Voice Catalog."""

    def __init__(
        self,
        voice_repo: IVoiceRepository,
        lesson_repo: ILessonRepository,
        storage_provider: IStorageProvider,
        voice_asset_provisioners: dict[TtsProvider, IVoiceAssetProvisioner],
        audio_processor: AudioProcessor | None = None,
    ) -> None:
        self._voice_repo = voice_repo
        self._lesson_repo = lesson_repo
        self._storage_provider = storage_provider
        self._voice_asset_provisioners = voice_asset_provisioners
        self._audio_processor = audio_processor or AudioProcessor()

    def _resolve_provisioner(self, tts_provider: str) -> IVoiceAssetProvisioner:
        try:
            provider_key = TtsProvider(tts_provider)
        except ValueError:
            raise UnsupportedVoiceTtsProviderException() from None

        provisioner = self._voice_asset_provisioners.get(provider_key)
        if provisioner is None:
            raise UnsupportedVoiceTtsProviderException()
        return provisioner

    def _optional_provisioner(self, tts_provider: str) -> IVoiceAssetProvisioner | None:
        try:
            provider_key = TtsProvider(tts_provider)
        except ValueError:
            return None
        return self._voice_asset_provisioners.get(provider_key)

    async def create_voice(
        self,
        session: Any,
        create_item: CreateVoiceDTO,
        reference_wav: bytes,
        current_user: UserDTO,
    ) -> VoiceDTO:
        """Create a catalog voice after external provisioning succeeds.

        See :mod:`senda.services.voice_provisioning` for pipeline order and
        idempotent retry semantics when Modal or S3 steps fail.
        """
        if await self._voice_repo.get_by_slug_or_none(
            session=session, slug=create_item.slug
        ):
            raise VoiceSlugAlreadyExistsException()

        provisioner = self._resolve_provisioner(create_item.tts_provider)

        logger.info(
            f"Creating new voice '{create_item.name}' (slug: {create_item.slug})"
        )

        assets = await provision_voice_assets(
            slug=create_item.slug,
            name=create_item.name,
            reference_wav=reference_wav,
            voice_asset_provisioner=provisioner,
            storage_provider=self._storage_provider,
            audio_processor=self._audio_processor,
        )

        voice_dto = await self._voice_repo.add(
            session=session,
            create_item=create_item,
            reference_s3_key=assets.reference_s3_key,
            sample_s3_key=assets.sample_s3_key,
        )

        logger.info(f"Voice '{create_item.slug}' created successfully")
        return voice_dto

    async def get_voice_by_slug(
        self, session: Any, slug: str, current_user: UserDTO
    ) -> VoiceDTO:
        """Fetch details of a single voice by its unique slug."""
        return await self._voice_repo.get_by_slug(session=session, slug=slug)

    async def list_voices(
        self, session: Any, active_only: bool, current_user: UserDTO
    ) -> list[VoiceDTO]:
        """List all voices in catalog."""
        if active_only:
            return await self._voice_repo.list_active(session=session)
        return await self._voice_repo.list_all(session=session)

    async def update_voice(
        self,
        session: Any,
        voice_id: UUID,
        update_item: UpdateVoiceDTO,
        current_user: UserDTO,
    ) -> VoiceDTO:
        """Update voice metadata (active flag, description)."""
        await self._voice_repo.get(session=session, voice_id=voice_id)

        return await self._voice_repo.update(
            session=session, voice_id=voice_id, update_item=update_item
        )

    async def delete_voice(
        self, session: Any, voice_id: UUID, current_user: UserDTO
    ) -> None:
        """Delete catalog voice and its remote/S3 artifacts.

        Order: remote provider assets → S3 reference/sample → DB row. This is not a
        distributed transaction; if a step fails after earlier ones succeeded, remote
        or S3 state may be partially removed while the catalog row remains.
        """
        voice = await self._voice_repo.get(session=session, voice_id=voice_id)

        lesson_count = await self._lesson_repo.count_using_voice(
            session=session, voice_id=voice_id
        )
        if lesson_count > 0:
            raise VoiceInUseException()

        logger.info(f"Deleting voice '{voice.slug}' ({voice_id})")

        if provisioner := self._optional_provisioner(voice.tts_provider):
            await provisioner.delete_remote_assets(voice.slug)

        await self._storage_provider.delete_file(voice.reference_s3_key)
        if voice.sample_s3_key:
            await self._storage_provider.delete_file(voice.sample_s3_key)

        await self._voice_repo.delete(session=session, voice_id=voice_id)

        logger.info(f"Voice '{voice.slug}' deleted successfully")
