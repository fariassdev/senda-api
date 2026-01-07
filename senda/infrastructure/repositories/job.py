from datetime import datetime
from typing import Any

from sqlalchemy import desc, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.exceptions import JobNotFoundException
from senda.domain.dtos.job import CreateJobDTO, JobRecordDTO, UpdateJobDTO
from senda.domain.mapper import IModelMapper
from senda.domain.repositories.job import IJobRepository
from senda.infrastructure.models import GenerationJob


class JobRepository(IJobRepository):
    """Implementation of job repository using SQLAlchemy."""

    def __init__(self, job_mapper: IModelMapper[GenerationJob, JobRecordDTO]):
        self._job_mapper = job_mapper

    async def create(
        self, session: AsyncSession, created_by: int, create_item: CreateJobDTO
    ) -> JobRecordDTO:
        query = (
            insert(GenerationJob)
            .values(
                job_type=create_item.job_type,
                course_id=create_item.course_id,
                lesson_id=create_item.lesson_id,
                payload=create_item.payload,
                status="pending",
                created_by=created_by,
                created_at=datetime.now(),
            )
            .returning(GenerationJob)
        )
        result = await session.execute(query)
        job = result.scalar()
        return self._job_mapper.to_dto(job)

    async def get_by_id(self, session: AsyncSession, job_id: int) -> JobRecordDTO:
        query = select(GenerationJob).where(GenerationJob.id == job_id)
        if not (job := await session.scalar(query)):
            raise JobNotFoundException()
        return self._job_mapper.to_dto(job)

    async def get_by_id_or_none(
        self, session: AsyncSession, job_id: int
    ) -> JobRecordDTO | None:
        query = select(GenerationJob).where(GenerationJob.id == job_id)
        if job := await session.scalar(query):
            return self._job_mapper.to_dto(job)
        return None

    async def list_by_filters(
        self,
        session: AsyncSession,
        limit: int,
        offset: int,
        status: str | None = None,
        job_type: str | None = None,
        course_id: int | None = None,
        lesson_id: int | None = None,
    ) -> list[JobRecordDTO]:
        query = select(GenerationJob).order_by(desc(GenerationJob.created_at))

        if status:
            query = query.where(GenerationJob.status == status)
        if job_type:
            query = query.where(GenerationJob.job_type == job_type)
        if course_id:
            query = query.where(GenerationJob.course_id == course_id)
        if lesson_id:
            query = query.where(GenerationJob.lesson_id == lesson_id)

        query = query.limit(limit).offset(offset)
        result = await session.execute(query)
        jobs = result.scalars().all()

        return [self._job_mapper.to_dto(job) for job in jobs]

    async def update_status(
        self,
        session: AsyncSession,
        job_id: int,
        status: str,
        started_at: Any | None = None,
        completed_at: Any | None = None,
        error_message: str | None = None,
        result: dict[str, Any] | None = None,
    ) -> JobRecordDTO:
        """Atomic status update using RETURNING for single-query operation (NFR11)."""
        values: dict[str, Any] = {"status": status}

        if started_at is not None:
            values["started_at"] = started_at
        if completed_at is not None:
            values["completed_at"] = completed_at
        if error_message is not None:
            values["error_message"] = error_message
        if result is not None:
            values["result"] = result

        query = (
            update(GenerationJob)
            .where(GenerationJob.id == job_id)
            .values(**values)
            .returning(GenerationJob)
        )

        job = await session.scalar(query)
        if not job:
            raise JobNotFoundException()

        return self._job_mapper.to_dto(job)

    async def update(
        self, session: AsyncSession, job_id: int, update_item: UpdateJobDTO
    ) -> JobRecordDTO:
        """Update job fields based on UpdateJobDTO fields."""
        values: dict[str, Any] = {}

        if update_item.status is not None:
            values["status"] = update_item.status
        if update_item.result is not None:
            values["result"] = update_item.result
        if update_item.error_message is not None:
            values["error_message"] = update_item.error_message
        if update_item.started_at is not None:
            values["started_at"] = update_item.started_at
        if update_item.completed_at is not None:
            values["completed_at"] = update_item.completed_at

        if not values:
            # No fields to update, just return the existing job
            return await self.get_by_id(session, job_id)

        query = (
            update(GenerationJob)
            .where(GenerationJob.id == job_id)
            .values(**values)
            .returning(GenerationJob)
        )

        job = await session.scalar(query)
        if not job:
            raise JobNotFoundException()

        return self._job_mapper.to_dto(job)

    async def count_by_filters(
        self,
        session: AsyncSession,
        status: str | None = None,
        job_type: str | None = None,
        course_id: int | None = None,
        lesson_id: int | None = None,
    ) -> int:
        query = select(func.count(GenerationJob.id))

        if status:
            query = query.where(GenerationJob.status == status)
        if job_type:
            query = query.where(GenerationJob.job_type == job_type)
        if course_id:
            query = query.where(GenerationJob.course_id == course_id)
        if lesson_id:
            query = query.where(GenerationJob.lesson_id == lesson_id)

        result = await session.execute(query)
        count = result.scalar()
        return count or 0
