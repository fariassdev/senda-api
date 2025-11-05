"""DTOs for AI-powered course generation."""

from dataclasses import dataclass

from senda.core.enums import DifficultyLevel


@dataclass(frozen=True)
class LessonStructureDTO:
    """Structure for a lesson to be generated."""

    title: str
    core_practice: str
    key_point: str
    tone: str
    duration_minutes: int
    order: int


@dataclass(frozen=True)
class CourseStructureDTO:
    """Complete course structure from AI generation."""

    title: str
    description: str
    duration_days: int
    difficulty_level: DifficultyLevel
    tags: list[str]
    lessons: list[LessonStructureDTO]

    @property
    def estimated_total_minutes(self) -> int:
        """Calculate total estimated minutes from lessons."""
        return sum(lesson.duration_minutes for lesson in self.lessons)


@dataclass(frozen=True)
class CourseGenerationRequestDTO:
    """Request parameters for course generation."""

    prompt: str
    user_id: int
    difficulty_level: DifficultyLevel | None = None
