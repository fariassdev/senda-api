"""Job service implementation with Cloud Tasks integration.

This module provides the concrete implementation of the job service,
handling job creation, retrieval, cancellation, and retry with
optional Cloud Tasks queue integration for asynchronous processing.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.exceptions import (
    CloudTasksException,
    JobNotCancellableException,
    JobNotRetryableException,
)
from senda.core.tasks import ICloudTasksClient
from senda.domain.dtos.job import CreateJobDTO, JobFiltersDTO, JobRecordDTO
from senda.domain.repositories.job import IJobRepository
from senda.domain.services.job import IJobService

logger = logging.getLogger(__name__)

# Status values for job state machine
CANCELLABLE_STATUSES = {"pending", "processing"}
RETRYABLE_STATUSES = {"failed"}


class JobService(IJobService):
    """Service for managing generation jobs with Cloud Tasks integration.

    This service implements the business logic for job management, including:
    - Creating jobs with automatic Cloud Tasks enqueuing
    - Retrieving and listing jobs with filtering
    - Cancelling jobs (with best-effort task deletion)
    - Retrying failed jobs

    Note: This service does NOT commit transactions. The API layer is responsible
    for transaction management via the Unit of Work pattern.
    """

    def __init__(
        self, job_repo: IJobRepository, tasks_client: ICloudTasksClient | None = None
    ):
        """
        Initialize the job service.

        Args:
            job_repo: Repository for job data access
            tasks_client: Optional Cloud Tasks client (None for local dev mode)
        """
        self._job_repo = job_repo
        self._tasks_client = tasks_client

    async def create_job(
        self, session: AsyncSession, user_id: int, request: CreateJobDTO
    ) -> JobRecordDTO:
        """Creates a job and enqueues a Cloud Task.

        If Cloud Tasks client is not configured (local dev mode), the job is
        created in the database but no task is enqueued. A warning is logged.

        If task creation fails after job record creation, the job status is
        updated to 'failed' to prevent orphan pending jobs (NFR12).
        """

        # Step 1: Create job record with status 'pending'
        job = await self._job_repo.create(session, user_id, request)
        logger.info(f"Created job {job.id} with type '{job.job_type}'")

        # Step 2: Enqueue Cloud Task (if client available)
        if self._tasks_client:
            try:
                task_name = await self._tasks_client.create_task(
                    job_id=job.id, job_type=job.job_type
                )
                logger.info(f"Job {job.id} created with task {task_name}")
            except CloudTasksException:
                # Rollback: Mark job as failed since we can't commit partial state
                # Note: We update status rather than delete because service
                # methods shouldn't call commit() - the API layer handles that
                await self._job_repo.update_status(
                    session,
                    job.id,
                    status="failed",
                    error_message="Failed to enqueue Cloud Task",
                    completed_at=datetime.now(timezone.utc),
                )
                raise
        else:
            logger.warning(
                f"Cloud Tasks client not configured. "
                f"Job {job.id} created but task not enqueued."
            )

        return job

    async def get_job(self, session: AsyncSession, job_id: int) -> JobRecordDTO:
        """Gets a job by ID."""
        return await self._job_repo.get_by_id(session, job_id)

    async def list_jobs(
        self, session: AsyncSession, filters: JobFiltersDTO
    ) -> list[JobRecordDTO]:
        """Lists jobs with filtering and pagination."""
        return await self._job_repo.list_by_filters(
            session,
            limit=filters.limit,
            offset=filters.offset,
            status=filters.status,
            job_type=filters.job_type,
            course_id=filters.course_id,
            lesson_id=filters.lesson_id,
        )

    async def count_jobs(self, session: AsyncSession, filters: JobFiltersDTO) -> int:
        """Counts jobs matching filters."""
        return await self._job_repo.count_by_filters(
            session,
            status=filters.status,
            job_type=filters.job_type,
            course_id=filters.course_id,
            lesson_id=filters.lesson_id,
        )

    async def cancel_job(self, session: AsyncSession, job_id: int) -> JobRecordDTO:
        """Cancels a pending or processing job.

        Note: Cloud Task deletion is best-effort. If we had the task name stored,
        we would attempt to delete it here. This is a future enhancement.
        """

        # Get current job
        job = await self._job_repo.get_by_id(session, job_id)

        # Validate status
        if job.status not in CANCELLABLE_STATUSES:
            raise JobNotCancellableException(
                message=f"Job with status '{job.status}' cannot be cancelled"
            )

        # Update status to cancelled
        updated_job = await self._job_repo.update_status(
            session, job_id, status="cancelled", completed_at=datetime.now(timezone.utc)
        )

        logger.info(f"Job {job_id} cancelled (previous status: {job.status})")

        # Best-effort: Try to delete the Cloud Task
        # Note: We don't have task_name stored, so this is a future enhancement

        return updated_job

    async def retry_job(self, session: AsyncSession, job_id: int) -> JobRecordDTO:
        """Retries a failed job by creating a new one with the same payload."""

        # Get original job
        original_job = await self._job_repo.get_by_id(session, job_id)

        # Validate status
        if original_job.status not in RETRYABLE_STATUSES:
            raise JobNotRetryableException(
                message=f"Job with status '{original_job.status}' cannot be retried"
            )

        # Create new job with same payload
        retry_request = CreateJobDTO(
            job_type=original_job.job_type,
            course_id=original_job.course_id,
            lesson_id=original_job.lesson_id,
            payload=original_job.payload,
        )

        # Use the original created_by for retry
        new_job = await self.create_job(session, original_job.created_by, retry_request)

        logger.info(f"Retried job {job_id} as new job {new_job.id}")

        return new_job
