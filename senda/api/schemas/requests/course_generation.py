"""Request schemas for AI-powered course generation."""

from pydantic import BaseModel, Field

from senda.core.enums import DifficultyLevel
from senda.domain.dtos.course_generation import CourseGenerationRequestDTO


class CourseGenerationRequest(BaseModel):
    """Request schema for AI-powered course generation."""

    prompt: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="Natural language description of the desired course",
        examples=["Create a 7-day mindfulness course for anxiety"],
    )

    difficulty_level: DifficultyLevel | None = Field(
        None, description="Target difficulty level", alias="difficultyLevel"
    )

    def to_dto(self, user_id: int) -> CourseGenerationRequestDTO:
        """
        Converts API request to domain DTO.

        Args:
            user_id: ID of the requesting user

        Returns:
            CourseGenerationRequestDTO for service layer
        """
        return CourseGenerationRequestDTO(
            prompt=self.prompt, user_id=user_id, difficulty_level=self.difficulty_level
        )
