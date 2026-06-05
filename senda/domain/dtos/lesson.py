import datetime
from dataclasses import dataclass
from uuid import UUID

from senda.core.enums import LessonStatus
from senda.domain.dtos.script_generation import ScriptPartDTO


@dataclass(frozen=True)
class LessonRecordDTO:
    """Raw lesson record from database."""

    id: int
    course_id: int
    lesson_number: int
    title: str
    core_practice: str
    key_point: str
    tone: str
    duration_minutes: int
    status: LessonStatus
    script: str | None
    audio_url: str | None
    script_generated_at: datetime.datetime | None
    audio_generated_at: datetime.datetime | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    voice_id: UUID | None = None


@dataclass(frozen=True)
class LessonDTO:
    """Full lesson DTO."""

    id: int
    course_id: int
    lesson_number: int
    title: str
    core_practice: str
    key_point: str
    tone: str
    duration_minutes: int
    status: LessonStatus
    script: list[ScriptPartDTO] | None
    audio_url: str | None
    script_generated_at: datetime.datetime | None
    audio_generated_at: datetime.datetime | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    voice_id: UUID | None = None


@dataclass(frozen=True)
class LessonsListDTO:
    """List of lessons with count."""

    lessons: list[LessonDTO]
    lessons_count: int


@dataclass(frozen=True)
class CreateLessonDTO:
    """DTO for creating a new lesson."""

    lesson_number: int
    title: str
    core_practice: str
    key_point: str
    tone: str
    duration_minutes: int


@dataclass(frozen=True)
class UpdateLessonDTO:
    """DTO for updating a lesson."""

    title: str | None = None
    core_practice: str | None = None
    key_point: str | None = None
    tone: str | None = None
    duration_minutes: int | None = None
    status: LessonStatus | None = None
    script: list[ScriptPartDTO] | None = None
    audio_url: str | None = None
    script_generated_at: datetime.datetime | None = None
    audio_generated_at: datetime.datetime | None = None
    voice_id: UUID | None = None


@dataclass(frozen=True)
class ReorderLessonDTO:
    """DTO for a single lesson reorder item."""

    lesson_id: int
    lesson_number: int


@dataclass(frozen=True)
class ReorderLessonsDTO:
    """DTO for reordering lessons."""

    lessons: list[ReorderLessonDTO]
