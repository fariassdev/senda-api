import datetime
from dataclasses import dataclass


@dataclass(frozen=True)
class JobRecordDTO:
    """Raw generation job record from database."""

    id: int
    job_type: str
    course_id: int
    lesson_id: int | None
    status: str
    payload: str | None
    result: str | None
    error_message: str | None
    created_at: datetime.datetime
    started_at: datetime.datetime | None
    completed_at: datetime.datetime | None
    created_by: int


@dataclass(frozen=True)
class JobDTO:
    """Full job DTO with all fields for API responses."""

    id: int
    job_type: str
    course_id: int
    lesson_id: int | None
    status: str
    payload: str | None
    result: str | None
    error_message: str | None
    created_at: datetime.datetime
    started_at: datetime.datetime | None
    completed_at: datetime.datetime | None
    created_by: int


@dataclass(frozen=True)
class CreateJobDTO:
    """DTO for creating a new generation job."""

    job_type: str
    course_id: int
    lesson_id: int | None = None
    payload: str | None = None


@dataclass(frozen=True)
class UpdateJobDTO:
    """DTO for updating a generation job status and results."""

    status: str | None = None
    result: str | None = None
    error_message: str | None = None
    started_at: datetime.datetime | None = None
    completed_at: datetime.datetime | None = None


@dataclass(frozen=True)
class JobListDTO:
    """List of jobs with count for pagination."""

    jobs: list[JobDTO]
    jobs_count: int
