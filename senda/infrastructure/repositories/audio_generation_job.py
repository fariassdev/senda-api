from datetime import datetime
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.enums import AudioGenerationJobStatus
from senda.core.exceptions import AudioGenerationJobNotFoundException
from senda.domain.dtos.audio_generation_job import (
    AudioGenerationJobDTO,
    CreateAudioGenerationJobDTO,
    UpdateAudioGenerationJobDTO,
)
from senda.domain.mapper import IModelMapper
from senda.domain.repositories.audio_generation_job import IAudioGenerationJobRepository
from senda.infrastructure.models import AudioGenerationJob

_ACTIVE_JOB_STATUSES = (
    AudioGenerationJobStatus.PENDING.value,
    AudioGenerationJobStatus.GENERATING.value,
)


class AudioGenerationJobRepository(IAudioGenerationJobRepository):
    def __init__(
        self, job_mapper: IModelMapper[AudioGenerationJob, AudioGenerationJobDTO]
    ):
        self._job_mapper = job_mapper

    async def add(
        self, session: AsyncSession, create_item: CreateAudioGenerationJobDTO
    ) -> AudioGenerationJobDTO:
        query = (
            insert(AudioGenerationJob)
            .values(
                id=create_item.id,
                lesson_id=create_item.lesson_id,
                voice_id=create_item.voice_id,
                voice_slug=create_item.voice_slug,
                audio_provider=create_item.audio_provider,
                s3_base_path=create_item.s3_base_path,
                status=AudioGenerationJobStatus.PENDING.value,
                segments_available=0,
                available_duration_ms=0,
                estimated_total_duration_ms=create_item.estimated_total_duration_ms,
                created_at=datetime.now(),
            )
            .returning(AudioGenerationJob)
        )
        result = await session.execute(query)
        return self._job_mapper.to_dto(result.scalar())

    async def get_or_none(
        self, session: AsyncSession, job_id: UUID
    ) -> AudioGenerationJobDTO | None:
        query = select(AudioGenerationJob).where(AudioGenerationJob.id == job_id)
        if job := await session.scalar(query):
            return self._job_mapper.to_dto(job)

    async def get(self, session: AsyncSession, job_id: UUID) -> AudioGenerationJobDTO:
        query = select(AudioGenerationJob).where(AudioGenerationJob.id == job_id)
        if not (job := await session.scalar(query)):
            raise AudioGenerationJobNotFoundException()
        return self._job_mapper.to_dto(job)

    async def get_active_for_lesson_voice(
        self, session: AsyncSession, lesson_id: int, voice_id: UUID
    ) -> AudioGenerationJobDTO | None:
        query = select(AudioGenerationJob).where(
            AudioGenerationJob.lesson_id == lesson_id,
            AudioGenerationJob.voice_id == voice_id,
            AudioGenerationJob.status.in_(_ACTIVE_JOB_STATUSES),
        )
        if job := await session.scalar(query):
            return self._job_mapper.to_dto(job)

    async def get_active_for_lesson(
        self, session: AsyncSession, lesson_id: int
    ) -> AudioGenerationJobDTO | None:
        query = (
            select(AudioGenerationJob)
            .where(
                AudioGenerationJob.lesson_id == lesson_id,
                AudioGenerationJob.status.in_(_ACTIVE_JOB_STATUSES),
            )
            .order_by(AudioGenerationJob.created_at.desc())
            .limit(1)
        )
        if job := await session.scalar(query):
            return self._job_mapper.to_dto(job)

    async def update(
        self,
        session: AsyncSession,
        job_id: UUID,
        update_item: UpdateAudioGenerationJobDTO,
    ) -> AudioGenerationJobDTO:
        query = (
            update(AudioGenerationJob)
            .where(AudioGenerationJob.id == job_id)
            .returning(AudioGenerationJob)
        )

        if update_item.status is not None:
            query = query.values(status=update_item.status.value)
        if update_item.segments_available is not None:
            query = query.values(segments_available=update_item.segments_available)
        if update_item.available_duration_ms is not None:
            query = query.values(
                available_duration_ms=update_item.available_duration_ms
            )
        if update_item.estimated_total_duration_ms is not None:
            query = query.values(
                estimated_total_duration_ms=update_item.estimated_total_duration_ms
            )
        if update_item.lesson_audio_id is not None:
            query = query.values(lesson_audio_id=update_item.lesson_audio_id)
        if update_item.error_message is not None:
            query = query.values(error_message=update_item.error_message)
        if update_item.started_at is not None:
            query = query.values(started_at=update_item.started_at)
        if update_item.completed_at is not None:
            query = query.values(completed_at=update_item.completed_at)

        result = await session.execute(query)
        if not (job := result.scalar()):
            raise AudioGenerationJobNotFoundException()
        return self._job_mapper.to_dto(job)
