"""Cloud Tasks client module for job queue management.

This module provides an abstract interface and implementation for Google Cloud Tasks,
enabling asynchronous job execution via task queues.
"""

import abc
import json
import logging
from datetime import datetime, timedelta, timezone

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from senda.core.exceptions import CloudTasksException
from senda.core.settings.base import BaseAppSettings

logger = logging.getLogger(__name__)


class ICloudTasksClient(abc.ABC):
    """Abstract interface for Cloud Tasks operations."""

    @abc.abstractmethod
    async def create_task(
        self, job_id: int, job_type: str, delay_seconds: int = 0
    ) -> str:
        """
        Creates a Cloud Task for the given job.

        Args:
            job_id: The job ID to process
            job_type: Type of job (e.g., "script_generation", "audio_generation")
            delay_seconds: Optional delay before task execution

        Returns:
            Task name (full resource path)

        Raises:
            CloudTasksException: If task creation fails
        """
        ...

    @abc.abstractmethod
    async def delete_task(self, task_name: str) -> bool:
        """
        Deletes a Cloud Task by name.

        Args:
            task_name: Full resource path of the task

        Returns:
            True if deleted, False if not found
        """
        ...


class CloudTasksClient(ICloudTasksClient):
    """Google Cloud Tasks client implementation.

    This client handles creating and deleting tasks in Google Cloud Tasks queues.
    Tasks are configured to call back to the internal callback endpoint with OIDC
    authentication for secure Cloud Run invocation.
    """

    def __init__(self, settings: BaseAppSettings):
        """
        Initialize the Cloud Tasks client.

        Args:
            settings: Application settings containing GCP configuration
        """
        self._client = tasks_v2.CloudTasksAsyncClient()
        self._project = settings.gcp_project_id
        self._location = settings.gcp_location
        self._queue = settings.gcp_queue_id
        self._service_url = settings.gcp_service_url
        self._invoker_email = settings.gcp_tasks_invoker_email

        self._parent = self._client.queue_path(
            self._project, self._location, self._queue
        )

    async def create_task(
        self, job_id: int, job_type: str, delay_seconds: int = 0
    ) -> str:
        """Creates a Cloud Task targeting the callback endpoint."""

        # Build callback URL
        callback_url = f"{self._service_url}/internal/tasks/callback"

        # Build task payload
        payload = {
            "job_id": job_id,
            "job_type": job_type,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Build HTTP request with OIDC token for Cloud Run authentication
        http_request = tasks_v2.HttpRequest(
            http_method=tasks_v2.HttpMethod.POST,
            url=callback_url,
            headers={"Content-Type": "application/json"},
            body=json.dumps(payload).encode(),
        )

        # Add OIDC token for Cloud Run invocation if service account is configured
        if self._invoker_email:
            http_request.oidc_token = tasks_v2.OidcToken(
                service_account_email=self._invoker_email, audience=self._service_url
            )

        # Build task
        task = tasks_v2.Task(http_request=http_request)

        # Set schedule time if delay is specified
        if delay_seconds > 0:
            schedule_time = datetime.now(timezone.utc) + timedelta(
                seconds=delay_seconds
            )
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(schedule_time)
            task.schedule_time = timestamp

        try:
            response = await self._client.create_task(parent=self._parent, task=task)
            logger.info(f"Created Cloud Task: {response.name} for job {job_id}")
            return response.name
        except Exception as e:
            logger.error(f"Failed to create Cloud Task for job {job_id}: {e}")
            raise CloudTasksException(message=f"Failed to enqueue task: {e}") from e

    async def delete_task(self, task_name: str) -> bool:
        """Deletes a Cloud Task by name."""
        try:
            await self._client.delete_task(name=task_name)
            logger.info(f"Deleted Cloud Task: {task_name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete Cloud Task {task_name}: {e}")
            return False
