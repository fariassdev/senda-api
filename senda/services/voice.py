import base64
import logging
from typing import Any
from uuid import UUID

from senda.core.enums import UserRole
from senda.core.exceptions import InsufficientPermissionsException
from senda.domain.dtos.user import UserDTO
from senda.domain.dtos.voice import CreateVoiceDTO, UpdateVoiceDTO, VoiceDTO
from senda.domain.repositories.voice import IVoiceRepository
from senda.domain.services.audio_generation import IStorageProvider
from senda.domain.services.voice import IVoiceService
from senda.infrastructure.providers.chatterbox_audio_provider import (
    ChatterboxAudioProvider,
)
from senda.infrastructure.utils.audio_processor import AudioProcessor

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
        """Create a new Voice in the catalog, syncs it to Modal, and generates a sample."""
        if current_user.role != UserRole.ADMIN:
            raise InsufficientPermissionsException()

        logger.info(
            f"Creating new voice '{create_item.name}' (slug: {create_item.slug})"
        )

        # 1. Upload reference WAV to private S3 folder
        reference_s3_key = f"voices/reference/{create_item.slug}.wav"
        await self._storage_provider.upload_file(
            file_data=reference_wav, key=reference_s3_key, content_type="audio/wav"
        )

        # 2. Save preliminary Voice in DB
        voice_dto = await self._voice_repo.add(
            session=session, create_item=create_item, reference_s3_key=reference_s3_key
        )

        try:
            # 3. Synchronize reference WAV with Modal Volume via API
            await self._chatterbox_provider.sync_voice_to_volume(
                voice_slug=create_item.slug, reference_wav=reference_wav
            )

            # 4. Generate sample text fixed preview
            preview_text = (
                f"Hello, I am {create_item.name}. Take a deep breath, relax, "
                f"and let me guide you on your journey to mindfulness with Senda."
            )
            sample_pcm = await self._chatterbox_provider.generate_speech(
                text=preview_text, voice=create_item.slug, speed=1.0
            )

            # 5. Convert sample PCM to MP3 and upload to S3
            sample_segment = self._audio_processor.pcm_to_audio_segment(sample_pcm)
            sample_mp3 = self._audio_processor.export_to_mp3(sample_segment)
            sample_s3_key = f"voices/samples/{create_item.slug}_sample.mp3"

            await self._storage_provider.upload_file(
                file_data=sample_mp3, key=sample_s3_key, content_type="audio/mpeg"
            )

            # 6. Update database record with success state and sample S3 URL
            voice_dto = await self._voice_repo.update(
                session=session,
                voice_id=voice_dto.id,
                update_item=UpdateVoiceDTO(
                    sample_s3_key=sample_s3_key,
                    is_synced_to_modal=True,
                    modal_sync_error=None,
                ),
            )

            logger.info(f"Voice '{create_item.slug}' fully integrated successfully")

        except Exception as e:
            logger.exception(
                f"Error during synchronization for voice '{create_item.slug}'"
            )
            # Log synchronization failure state into DB
            voice_dto = await self._voice_repo.update(
                session=session,
                voice_id=voice_dto.id,
                update_item=UpdateVoiceDTO(
                    is_synced_to_modal=False, modal_sync_error=str(e)
                ),
            )
            raise

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

        # Check existence
        await self._voice_repo.get(session=session, voice_id=voice_id)

        return await self._voice_repo.update(
            session=session, voice_id=voice_id, update_item=update_item
        )
