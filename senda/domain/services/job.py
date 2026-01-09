"""Job service interface for Clean Architecture pattern.

This module defines the abstract interface for job service operations,
enabling dependency injection and testability.
"""

import abc
from typing import Any

from senda.domain.dtos.job import CreateJobDTO, JobFiltersDTO, JobRecordDTO


class IJobService(abc.ABC):
    """Abstract interface for job service operations.

    This interface defines the contract for job management operations,
    including job creation with Cloud Tasks integration, retrieval,
    listing, cancellation, and retry functionality.
    """

    @abc.abstractmethod
    async def create_job(
        self, session: Any, user_id: int, request: CreateJobDTO
    ) -> JobRecordDTO:
        """
        Creates a job and enqueues a Cloud Task.

        Args:
            session: Database session
            user_id: ID of the user creating the job
            request: Job creation data

        Returns:
            JobRecordDTO of the created job

        Raises:
            CloudTasksException: If task enqueue fails (job is rolled back)
        """
        ...

    @abc.abstractmethod
    async def get_job(self, session: Any, job_id: int) -> JobRecordDTO:
        """
        Gets a job by ID.

        Args:
            session: Database session
            job_id: ID of the job to retrieve

        Returns:
            JobRecordDTO of the job

        Raises:
            JobNotFoundException: If job doesn't exist
        """
        ...

    @abc.abstractmethod
    async def list_jobs(
        self, session: Any, filters: JobFiltersDTO
    ) -> list[JobRecordDTO]:
        """
        Lists jobs with filtering and pagination.

        Args:
            session: Database session
            filters: Filtering and pagination options

        Returns:
            List of JobRecordDTO matching the filters
        """
        ...

    @abc.abstractmethod
    async def count_jobs(self, session: Any, filters: JobFiltersDTO) -> int:
        """
        Counts jobs matching filters.

        Args:
            session: Database session
            filters: Filtering options

        Returns:
            Count of matching jobs
        """
        ...

    @abc.abstractmethod
    async def cancel_job(self, session: Any, job_id: int) -> JobRecordDTO:
        """
        Cancels a pending or processing job.

        Args:
            session: Database session
            job_id: ID of the job to cancel

        Returns:
            JobRecordDTO of the cancelled job

        Raises:
            JobNotFoundException: If job doesn't exist
            JobNotCancellableException: If job status is not cancellable
        """
        ...

    @abc.abstractmethod
    async def retry_job(self, session: Any, job_id: int) -> JobRecordDTO:
        """
        Retries a failed job by creating a new one with the same payload.

        Args:
            session: Database session
            job_id: ID of the failed job to retry

        Returns:
            JobRecordDTO of the new job

        Raises:
            JobNotFoundException: If job doesn't exist
            JobNotRetryableException: If job status is not failed
        """
        ...
