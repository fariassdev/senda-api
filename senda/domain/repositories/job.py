import abc
from typing import Any

from senda.domain.dtos.job import CreateJobDTO, JobRecordDTO, UpdateJobDTO


class IJobRepository(abc.ABC):
    """Job repository interface following Clean Architecture patterns."""

    @abc.abstractmethod
    async def create(
        self, session: Any, created_by: int, create_item: CreateJobDTO
    ) -> JobRecordDTO: ...

    @abc.abstractmethod
    async def get_by_id(self, session: Any, job_id: int) -> JobRecordDTO: ...

    @abc.abstractmethod
    async def get_by_id_or_none(
        self, session: Any, job_id: int
    ) -> JobRecordDTO | None: ...

    @abc.abstractmethod
    async def list_by_filters(
        self,
        session: Any,
        limit: int,
        offset: int,
        status: str | None = None,
        job_type: str | None = None,
        course_id: int | None = None,
        lesson_id: int | None = None,
    ) -> list[JobRecordDTO]: ...

    @abc.abstractmethod
    async def update_status(
        self,
        session: Any,
        job_id: int,
        status: str,
        started_at: Any | None = None,
        completed_at: Any | None = None,
        error_message: str | None = None,
        result: dict | None = None,
    ) -> JobRecordDTO: ...

    @abc.abstractmethod
    async def update(
        self, session: Any, job_id: int, update_item: UpdateJobDTO
    ) -> JobRecordDTO: ...

    @abc.abstractmethod
    async def count_by_filters(
        self,
        session: Any,
        status: str | None = None,
        job_type: str | None = None,
        course_id: int | None = None,
        lesson_id: int | None = None,
    ) -> int: ...
