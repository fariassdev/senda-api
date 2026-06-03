import logging
from typing import Any
from uuid import UUID

from senda.core.enums import UserRole
from senda.core.exceptions import (
    InsufficientPermissionsException,
    VoiceSlugAlreadyExistsException,
)
from senda.domain.dtos.user import UserDTO
from senda.domain.dtos.voice import CreateVoiceDTO, UpdateVoiceDTO, VoiceDTO
from senda.domain.repositories.voice import IVoiceRepository
from senda.domain.services.audio_generation import IStorageProvider
from senda.domain.services.voice import IVoiceService
from senda.infrastructure.providers.chatterbox_audio_provider import (
    ChatterboxAudioProvider,
)
from senda.infrastructure.utils.audio_processor import AudioProcessor
from senda.services.voice_provisioning import provision_voice_assets

logger = logging.getLogger(__name__)


class VoiceService(IVoiceService):
    """Business logic service for managing the Senda Voice Catalog."""

    def __init__(
        self,
        voice_repo: IVoiceRepository,
        storage_provider: IStorageProvider,
        chatterbox_provider: ChatterboxAudioProvider,
        audio_processor: AudioProcessor | None = None,
    ) -> None:
        self._voice_repo = voice_repo
        self._storage_provider = storage_provider
        self._chatterbox_provider = chatterbox_provider
        self._audio_processor = audio_processor or AudioProcessor()

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
        if current_user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        if await self._voice_repo.get_by_slug_or_none(
            session=session, slug=create_item.slug
        ):
            raise VoiceSlugAlreadyExistsException()

        logger.info(
            f"Creating new voice '{create_item.name}' (slug: {create_item.slug})"
        )

        assets = await provision_voice_assets(
            slug=create_item.slug,
            name=create_item.name,
            reference_wav=reference_wav,
            chatterbox_provider=self._chatterbox_provider,
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
        if current_user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        return await self._voice_repo.get_by_slug(session=session, slug=slug)

    async def list_voices(
        self, session: Any, active_only: bool, current_user: UserDTO
    ) -> list[VoiceDTO]:
        """List all voices in catalog."""
        if current_user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

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
        """Update voice configurations."""
        if current_user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        await self._voice_repo.get(session=session, voice_id=voice_id)

        return await self._voice_repo.update(
            session=session, voice_id=voice_id, update_item=update_item
        )
