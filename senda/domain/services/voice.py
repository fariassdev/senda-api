import abc
from typing import Any
from uuid import UUID

from senda.domain.dtos.user import UserDTO
from senda.domain.dtos.voice import CreateVoiceDTO, UpdateVoiceDTO, VoiceDTO


class IVoiceService(abc.ABC):
    """Voice service interface."""

    @abc.abstractmethod
    async def create_voice(
        self,
        session: Any,
        create_item: CreateVoiceDTO,
        reference_wav: bytes,
        current_user: UserDTO,
    ) -> VoiceDTO:
        """Provision Modal/S3 assets, then insert the catalog row.

        Raises:
            VoiceSlugAlreadyExistsException: Slug already in the database (409).
            UnsupportedVoiceTtsProviderException: No asset provisioner for tts_provider (400).
            AudioProviderException: Modal sync or TTS failed (502).
            StorageProviderException: S3 upload failed (502).
        """
        ...

    @abc.abstractmethod
    async def get_voice_by_slug(
        self, session: Any, slug: str, current_user: UserDTO
    ) -> VoiceDTO: ...

    @abc.abstractmethod
    async def list_voices(
        self, session: Any, active_only: bool, current_user: UserDTO
    ) -> list[VoiceDTO]: ...

    @abc.abstractmethod
    async def update_voice(
        self,
        session: Any,
        voice_id: UUID,
        update_item: UpdateVoiceDTO,
        current_user: UserDTO,
    ) -> VoiceDTO: ...

    @abc.abstractmethod
    async def delete_voice(
        self, session: Any, voice_id: UUID, current_user: UserDTO
    ) -> None:
        """Remove a voice from remote storage, S3, and the catalog.

        Raises:
            VoiceNotFoundException: Voice id not found (404).
            VoiceInUseException: One or more lessons reference this voice (409).
            AudioProviderException: Remote deletion failed (502).
            StorageProviderException: S3 deletion failed (502).

        See :mod:`senda.services.voice_provisioning` for pipeline order and idempotent
        retry semantics when remote or S3 steps fail before the DB row is removed.
        """
        ...
