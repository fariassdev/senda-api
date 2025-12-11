"""DTOs for lesson script generation."""

from dataclasses import dataclass
from typing import Any

from senda.core.enums import ScriptPartType


@dataclass(frozen=True)
class ScriptPartDTO:
    """Individual script part with type, content, and optional duration."""

    type: ScriptPartType
    content: str | None = None
    duration: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert individual script part to dictionary for serialization."""
        return {
            "type": self.type.value,
            "content": self.content,
            "duration": self.duration,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScriptPartDTO":
        """Create ScriptPartDTO from dictionary."""
        return cls(
            type=ScriptPartType(data["type"]),
            content=data.get("content"),
            duration=data.get("duration"),
        )


@dataclass(frozen=True)
class LessonScriptRequestDTO:
    """Request for generating a lesson script."""

    lesson_id: int
    user_id: int


@dataclass(frozen=True)
class CourseScriptRequestDTO:
    """Request for generating scripts for all lessons in a course."""

    user_id: int
    slug: str


@dataclass(frozen=True)
class ScriptGenerationResultDTO:
    """Result of script generation with generated script parts."""

    lesson_id: int
    script: list[ScriptPartDTO]
    generation_time_seconds: float | None = None


@dataclass(frozen=True)
class LessonContextDTO:
    """Context information for lesson script generation."""

    lesson_number: int
    title: str
    core_practice: str
    duration_minutes: int
    key_point: str
    tone: str


@dataclass(frozen=True)
class CourseContextDTO:
    """Course context information for script generation."""

    name: str
    description: str
    total_lessons: int
