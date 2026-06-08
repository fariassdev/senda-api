import abc
from typing import Any
from uuid import UUID

from senda.domain.dtos.lesson_audio import LessonAudioDTO, UpsertLessonAudioDTO


class ILessonAudioRepository(abc.ABC):
    """Repository interface for lesson HLS audio artifacts."""

    @abc.abstractmethod
    async def get_or_none(
        self, session: Any, lesson_audio_id: UUID
    ) -> LessonAudioDTO | None: ...

    @abc.abstractmethod
    async def get_by_lesson_and_voice(
        self, session: Any, lesson_id: int, voice_id: UUID
    ) -> LessonAudioDTO | None: ...

    @abc.abstractmethod
    async def list_by_lesson(
        self, session: Any, lesson_id: int
    ) -> list[LessonAudioDTO]: ...

    @abc.abstractmethod
    async def upsert(
        self, session: Any, upsert_item: UpsertLessonAudioDTO
    ) -> LessonAudioDTO: ...

    @abc.abstractmethod
    async def count_using_voice(self, session: Any, voice_id: UUID) -> int: ...
