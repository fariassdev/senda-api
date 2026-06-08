from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count

from senda.domain.dtos.lesson_audio import LessonAudioDTO, UpsertLessonAudioDTO
from senda.domain.mapper import IModelMapper
from senda.domain.repositories.lesson_audio import ILessonAudioRepository
from senda.infrastructure.models import LessonAudio


class LessonAudioRepository(ILessonAudioRepository):
    def __init__(self, lesson_audio_mapper: IModelMapper[LessonAudio, LessonAudioDTO]):
        self._lesson_audio_mapper = lesson_audio_mapper

    async def get_or_none(
        self, session: AsyncSession, lesson_audio_id: UUID
    ) -> LessonAudioDTO | None:
        query = select(LessonAudio).where(LessonAudio.id == lesson_audio_id)
        if lesson_audio := await session.scalar(query):
            return self._lesson_audio_mapper.to_dto(lesson_audio)

    async def get_by_lesson_and_voice(
        self, session: AsyncSession, lesson_id: int, voice_id: UUID
    ) -> LessonAudioDTO | None:
        query = select(LessonAudio).where(
            LessonAudio.lesson_id == lesson_id, LessonAudio.voice_id == voice_id
        )
        if lesson_audio := await session.scalar(query):
            return self._lesson_audio_mapper.to_dto(lesson_audio)

    async def list_by_lesson(
        self, session: AsyncSession, lesson_id: int
    ) -> list[LessonAudioDTO]:
        query = (
            select(LessonAudio)
            .where(LessonAudio.lesson_id == lesson_id)
            .order_by(LessonAudio.generated_at.desc())
        )
        rows = await session.scalars(query)
        return [self._lesson_audio_mapper.to_dto(row) for row in rows]

    async def upsert(
        self, session: AsyncSession, upsert_item: UpsertLessonAudioDTO
    ) -> LessonAudioDTO:
        now = datetime.now()
        query = (
            pg_insert(LessonAudio)
            .values(
                lesson_id=upsert_item.lesson_id,
                voice_id=upsert_item.voice_id,
                voice_slug=upsert_item.voice_slug,
                audio_provider=upsert_item.audio_provider,
                playlist_url=upsert_item.playlist_url,
                hls_base_path=upsert_item.hls_base_path,
                duration_ms=upsert_item.duration_ms,
                generated_at=upsert_item.generated_at,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_update(
                index_elements=["lesson_id", "voice_id"],
                set_={
                    "voice_slug": upsert_item.voice_slug,
                    "audio_provider": upsert_item.audio_provider,
                    "playlist_url": upsert_item.playlist_url,
                    "hls_base_path": upsert_item.hls_base_path,
                    "duration_ms": upsert_item.duration_ms,
                    "generated_at": upsert_item.generated_at,
                    "updated_at": now,
                },
            )
            .returning(LessonAudio)
        )
        result = await session.execute(query)
        return self._lesson_audio_mapper.to_dto(result.scalar())

    async def count_using_voice(self, session: AsyncSession, voice_id: UUID) -> int:
        query = (
            select(count())
            .select_from(LessonAudio)
            .where(LessonAudio.voice_id == voice_id)
        )
        result = await session.scalar(query)
        return int(result or 0)
