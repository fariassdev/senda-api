import abc
from typing import Any
from uuid import UUID

from senda.domain.dtos.audio_generation_job import (
    AudioGenerationJobDTO,
    CreateAudioGenerationJobDTO,
    UpdateAudioGenerationJobDTO,
)


class IAudioGenerationJobRepository(abc.ABC):
    """Repository interface for HLS audio generation jobs."""

    @abc.abstractmethod
    async def add(
        self, session: Any, create_item: CreateAudioGenerationJobDTO
    ) -> AudioGenerationJobDTO: ...

    @abc.abstractmethod
    async def get_or_none(
        self, session: Any, job_id: UUID
    ) -> AudioGenerationJobDTO | None: ...

    @abc.abstractmethod
    async def get(self, session: Any, job_id: UUID) -> AudioGenerationJobDTO: ...

    @abc.abstractmethod
    async def get_active_for_lesson_voice(
        self, session: Any, lesson_id: int, voice_id: UUID
    ) -> AudioGenerationJobDTO | None: ...

    @abc.abstractmethod
    async def update(
        self, session: Any, job_id: UUID, update_item: UpdateAudioGenerationJobDTO
    ) -> AudioGenerationJobDTO: ...
