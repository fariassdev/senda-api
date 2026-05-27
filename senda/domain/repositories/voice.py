import abc
from typing import Any
from uuid import UUID

from senda.domain.dtos.voice import CreateVoiceDTO, UpdateVoiceDTO, VoiceDTO


class IVoiceRepository(abc.ABC):
    """Voice repository interface."""

    @abc.abstractmethod
    async def add(
        self, session: Any, create_item: CreateVoiceDTO, reference_s3_key: str
    ) -> VoiceDTO: ...

    @abc.abstractmethod
    async def get_or_none(self, session: Any, voice_id: UUID) -> VoiceDTO | None: ...

    @abc.abstractmethod
    async def get(self, session: Any, voice_id: UUID) -> VoiceDTO: ...

    @abc.abstractmethod
    async def get_by_slug_or_none(self, session: Any, slug: str) -> VoiceDTO | None: ...

    @abc.abstractmethod
    async def get_by_slug(self, session: Any, slug: str) -> VoiceDTO: ...

    @abc.abstractmethod
    async def list_active(self, session: Any) -> list[VoiceDTO]: ...

    @abc.abstractmethod
    async def list_all(self, session: Any) -> list[VoiceDTO]: ...

    @abc.abstractmethod
    async def update(
        self, session: Any, voice_id: UUID, update_item: UpdateVoiceDTO
    ) -> VoiceDTO: ...

    @abc.abstractmethod
    async def delete(self, session: Any, voice_id: UUID) -> None: ...
