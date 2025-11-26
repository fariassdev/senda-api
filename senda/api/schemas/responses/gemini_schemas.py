"""
Pydantic schemas that define the contract with Gemini API.
These match the JSON structure that Gemini returns.
Used by infrastructure layer for Gemini response_schema parameter.
"""

from pydantic import BaseModel, Field

from senda.core.enums import DifficultyLevel


class GeminiLessonSchema(BaseModel):
    """Schema for lesson structure returned by Gemini API."""

    title: str = Field(..., description="Lesson title")
    core_practice: str = Field(..., description="Core mindfulness practice")
    key_point: str = Field(..., description="Key learning point")
    tone: str = Field(..., description="Tone/mood for the lesson")
    duration_minutes: int = Field(..., ge=1, description="Lesson duration in minutes")
    order: int = Field(..., ge=1, description="Lesson order in course")


class GeminiCourseSchema(BaseModel):
    """Schema for course structure returned by Gemini API."""

    title: str = Field(..., description="Course title")
    description: str = Field(..., description="Course description")
    duration_days: int = Field(..., ge=1, description="Course duration in days")
    difficulty_level: DifficultyLevel = Field(
        ..., description="Difficulty level (BEGINNER, INTERMEDIATE, or ADVANCED)"
    )
    tags: list[str] = Field(default_factory=list, description="Course tags")
    lessons: list[GeminiLessonSchema] = Field(..., description="Course lessons")
