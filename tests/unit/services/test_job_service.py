"""
Test suite for JobService with Cloud Tasks integration.
Tests business logic without database or external API calls.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.exceptions import (
    CloudTasksException,
    JobNotCancellableException,
    JobNotFoundException,
    JobNotRetryableException,
)
from senda.domain.dtos.job import CreateJobDTO, JobFiltersDTO, JobRecordDTO
from senda.services.job import JobService


class TestJobServiceCreate:
    """Test suite for JobService.create_job"""

    @pytest.fixture
    def mock_job_repo(self):
        """Mock job repository"""
        return AsyncMock()

    @pytest.fixture
    def mock_tasks_client(self):
        """Mock Cloud Tasks client"""
        return AsyncMock()

    @pytest.fixture
    def mock_session(self):
        """Mock database session"""
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def sample_job_record(self):
        """Sample job record DTO"""
        return JobRecordDTO(
            id=1,
            job_type="script_generation",
            course_id=10,
            lesson_id=100,
            status="pending",
            payload={"key": "value"},
            result=None,
            error_message=None,
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
            created_by=5,
        )

    @pytest.fixture
    def sample_create_request(self):
        """Sample create job request"""
        return CreateJobDTO(
            job_type="script_generation",
            course_id=10,
            lesson_id=100,
            payload={"key": "value"},
        )

    @pytest.mark.asyncio
    async def test_create_job_with_tasks_client_success(
        self,
        mock_job_repo,
        mock_tasks_client,
        mock_session,
        sample_job_record,
        sample_create_request,
    ):
        """Test successful job creation with Cloud Tasks enqueue"""
        # Setup
        mock_job_repo.create.return_value = sample_job_record
        mock_tasks_client.create_task.return_value = (
            "projects/p/locations/l/queues/q/tasks/t"
        )

        service = JobService(job_repo=mock_job_repo, tasks_client=mock_tasks_client)

        # Execute
        result = await service.create_job(
            session=mock_session, user_id=5, request=sample_create_request
        )

        # Assert
        assert result.id == 1
        assert result.status == "pending"
        mock_job_repo.create.assert_called_once_with(
            mock_session, 5, sample_create_request
        )
        mock_tasks_client.create_task.assert_called_once_with(
            job_id=1, job_type="script_generation"
        )

    @pytest.mark.asyncio
    async def test_create_job_without_tasks_client(
        self, mock_job_repo, mock_session, sample_job_record, sample_create_request
    ):
        """Test job creation without Cloud Tasks client (local dev mode)"""
        # Setup
        mock_job_repo.create.return_value = sample_job_record
        service = JobService(job_repo=mock_job_repo, tasks_client=None)

        # Execute
        result = await service.create_job(
            session=mock_session, user_id=5, request=sample_create_request
        )

        # Assert - job created but no task enqueued
        assert result.id == 1
        mock_job_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_job_task_creation_fails_updates_status(
        self,
        mock_job_repo,
        mock_tasks_client,
        mock_session,
        sample_job_record,
        sample_create_request,
    ):
        """Test job status updated to failed when task creation fails"""
        # Setup
        mock_job_repo.create.return_value = sample_job_record
        mock_tasks_client.create_task.side_effect = CloudTasksException(
            message="Failed to enqueue"
        )

        service = JobService(job_repo=mock_job_repo, tasks_client=mock_tasks_client)

        # Execute & Assert
        with pytest.raises(CloudTasksException):
            await service.create_job(
                session=mock_session, user_id=5, request=sample_create_request
            )

        # Verify job status was updated to failed
        mock_job_repo.update_status.assert_called_once()
        call_args = mock_job_repo.update_status.call_args
        assert call_args[0][1] == 1  # job_id
        assert call_args[1]["status"] == "failed"
        assert "Failed to enqueue" in call_args[1]["error_message"]


class TestJobServiceGet:
    """Test suite for JobService.get_job"""

    @pytest.fixture
    def mock_job_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def sample_job_record(self):
        return JobRecordDTO(
            id=1,
            job_type="audio_generation",
            course_id=10,
            lesson_id=100,
            status="processing",
            payload=None,
            result=None,
            error_message=None,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            created_by=5,
        )

    @pytest.mark.asyncio
    async def test_get_job_success(
        self, mock_job_repo, mock_session, sample_job_record
    ):
        """Test successful job retrieval"""
        mock_job_repo.get_by_id.return_value = sample_job_record
        service = JobService(job_repo=mock_job_repo)

        result = await service.get_job(mock_session, job_id=1)

        assert result.id == 1
        assert result.status == "processing"
        mock_job_repo.get_by_id.assert_called_once_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, mock_job_repo, mock_session):
        """Test job not found exception"""
        mock_job_repo.get_by_id.side_effect = JobNotFoundException()
        service = JobService(job_repo=mock_job_repo)

        with pytest.raises(JobNotFoundException):
            await service.get_job(mock_session, job_id=999)


class TestJobServiceList:
    """Test suite for JobService.list_jobs and count_jobs"""

    @pytest.fixture
    def mock_job_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def sample_filters(self):
        return JobFiltersDTO(
            status="pending",
            job_type="script_generation",
            course_id=10,
            lesson_id=None,
            limit=20,
            offset=0,
        )

    @pytest.fixture
    def sample_job_list(self):
        return [
            JobRecordDTO(
                id=i,
                job_type="script_generation",
                course_id=10,
                lesson_id=None,
                status="pending",
                payload=None,
                result=None,
                error_message=None,
                created_at=datetime.now(timezone.utc),
                started_at=None,
                completed_at=None,
                created_by=5,
            )
            for i in range(3)
        ]

    @pytest.mark.asyncio
    async def test_list_jobs_with_filters(
        self, mock_job_repo, mock_session, sample_filters, sample_job_list
    ):
        """Test job listing with filters"""
        mock_job_repo.list_by_filters.return_value = sample_job_list
        service = JobService(job_repo=mock_job_repo)

        result = await service.list_jobs(mock_session, sample_filters)

        assert len(result) == 3
        mock_job_repo.list_by_filters.assert_called_once_with(
            mock_session,
            limit=20,
            offset=0,
            status="pending",
            job_type="script_generation",
            course_id=10,
            lesson_id=None,
        )

    @pytest.mark.asyncio
    async def test_count_jobs_with_filters(
        self, mock_job_repo, mock_session, sample_filters
    ):
        """Test job counting with filters"""
        mock_job_repo.count_by_filters.return_value = 42
        service = JobService(job_repo=mock_job_repo)

        result = await service.count_jobs(mock_session, sample_filters)

        assert result == 42
        mock_job_repo.count_by_filters.assert_called_once_with(
            mock_session,
            status="pending",
            job_type="script_generation",
            course_id=10,
            lesson_id=None,
        )


class TestJobServiceCancel:
    """Test suite for JobService.cancel_job"""

    @pytest.fixture
    def mock_job_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=AsyncSession)

    def _make_job(self, status: str) -> JobRecordDTO:
        return JobRecordDTO(
            id=1,
            job_type="script_generation",
            course_id=10,
            lesson_id=100,
            status=status,
            payload=None,
            result=None,
            error_message=None,
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
            created_by=5,
        )

    @pytest.mark.asyncio
    async def test_cancel_pending_job_success(self, mock_job_repo, mock_session):
        """Test cancelling a pending job"""
        pending_job = self._make_job("pending")
        cancelled_job = self._make_job("cancelled")

        mock_job_repo.get_by_id.return_value = pending_job
        mock_job_repo.update_status.return_value = cancelled_job

        service = JobService(job_repo=mock_job_repo)
        result = await service.cancel_job(mock_session, job_id=1)

        assert result.status == "cancelled"
        mock_job_repo.update_status.assert_called_once()
        call_args = mock_job_repo.update_status.call_args
        assert call_args[1]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_processing_job_success(self, mock_job_repo, mock_session):
        """Test cancelling a processing job"""
        processing_job = self._make_job("processing")
        cancelled_job = self._make_job("cancelled")

        mock_job_repo.get_by_id.return_value = processing_job
        mock_job_repo.update_status.return_value = cancelled_job

        service = JobService(job_repo=mock_job_repo)
        result = await service.cancel_job(mock_session, job_id=1)

        assert result.status == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_completed_job_fails(self, mock_job_repo, mock_session):
        """Test that completed jobs cannot be cancelled"""
        completed_job = self._make_job("completed")
        mock_job_repo.get_by_id.return_value = completed_job

        service = JobService(job_repo=mock_job_repo)

        with pytest.raises(JobNotCancellableException) as exc_info:
            await service.cancel_job(mock_session, job_id=1)

        assert "completed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cancel_failed_job_fails(self, mock_job_repo, mock_session):
        """Test that failed jobs cannot be cancelled"""
        failed_job = self._make_job("failed")
        mock_job_repo.get_by_id.return_value = failed_job

        service = JobService(job_repo=mock_job_repo)

        with pytest.raises(JobNotCancellableException):
            await service.cancel_job(mock_session, job_id=1)


class TestJobServiceRetry:
    """Test suite for JobService.retry_job"""

    @pytest.fixture
    def mock_job_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_tasks_client(self):
        return AsyncMock()

    @pytest.fixture
    def mock_session(self):
        return Mock(spec=AsyncSession)

    def _make_job(self, status: str, job_id: int = 1) -> JobRecordDTO:
        return JobRecordDTO(
            id=job_id,
            job_type="audio_generation",
            course_id=10,
            lesson_id=100,
            status=status,
            payload={"voice": "en-us"},
            result=None,
            error_message="Previous failure" if status == "failed" else None,
            created_at=datetime.now(timezone.utc),
            started_at=None,
            completed_at=None,
            created_by=5,
        )

    @pytest.mark.asyncio
    async def test_retry_failed_job_success(
        self, mock_job_repo, mock_tasks_client, mock_session
    ):
        """Test successful retry of a failed job"""
        failed_job = self._make_job("failed", job_id=1)
        new_job = self._make_job("pending", job_id=2)

        mock_job_repo.get_by_id.return_value = failed_job
        mock_job_repo.create.return_value = new_job
        mock_tasks_client.create_task.return_value = "task-name"

        service = JobService(job_repo=mock_job_repo, tasks_client=mock_tasks_client)
        result = await service.retry_job(mock_session, job_id=1)

        assert result.id == 2
        assert result.status == "pending"

        # Verify new job was created with same payload
        create_call = mock_job_repo.create.call_args
        create_dto = create_call[0][2]
        assert create_dto.job_type == "audio_generation"
        assert create_dto.course_id == 10
        assert create_dto.lesson_id == 100
        assert create_dto.payload == {"voice": "en-us"}

    @pytest.mark.asyncio
    async def test_retry_pending_job_fails(self, mock_job_repo, mock_session):
        """Test that pending jobs cannot be retried"""
        pending_job = self._make_job("pending")
        mock_job_repo.get_by_id.return_value = pending_job

        service = JobService(job_repo=mock_job_repo)

        with pytest.raises(JobNotRetryableException) as exc_info:
            await service.retry_job(mock_session, job_id=1)

        assert "pending" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_completed_job_fails(self, mock_job_repo, mock_session):
        """Test that completed jobs cannot be retried"""
        completed_job = self._make_job("completed")
        mock_job_repo.get_by_id.return_value = completed_job

        service = JobService(job_repo=mock_job_repo)

        with pytest.raises(JobNotRetryableException):
            await service.retry_job(mock_session, job_id=1)

    @pytest.mark.asyncio
    async def test_retry_job_not_found(self, mock_job_repo, mock_session):
        """Test retry of non-existent job"""
        mock_job_repo.get_by_id.side_effect = JobNotFoundException()

        service = JobService(job_repo=mock_job_repo)

        with pytest.raises(JobNotFoundException):
            await service.retry_job(mock_session, job_id=999)
