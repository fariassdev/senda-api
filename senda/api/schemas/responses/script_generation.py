"""Response schemas for script generation API endpoints."""

from pydantic import BaseModel, Field

from senda.core.enums import ScriptPartType
from senda.domain.dtos.script_generation import (
    BatchScriptGenerationResultDTO,
    ScriptGenerationResultDTO,
)


class ScriptPartResponse(BaseModel):
    """Individual script part in API response."""

    type: ScriptPartType = Field(
        ..., description="Type of script part (speak or pause)"
    )
    content: str | None = Field(
        None, description="Content text for speak parts, null for pause parts"
    )
    duration: float | None = Field(
        None, description="Duration in seconds for pause parts, optional for speak"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "examples": [
                {"type": "speak", "content": "Welcome back to Senda..."},
                {"type": "pause", "duration": 3.0},
            ]
        }


class ScriptGenerationResponse(BaseModel):
    """Response for script generation request."""

    lesson_id: int = Field(..., description="ID of the lesson")
    script: list[ScriptPartResponse] = Field(..., description="Generated script parts")
    generation_time_seconds: float | None = Field(
        None, description="Time taken to generate the script"
    )

    @classmethod
    def from_dto(cls, dto: ScriptGenerationResultDTO) -> "ScriptGenerationResponse":
        """Create response from domain DTO."""
        return cls(
            lesson_id=dto.lesson_id,
            script=[
                ScriptPartResponse(
                    type=part.type, content=part.content, duration=part.duration
                )
                for part in dto.script
            ],
            generation_time_seconds=dto.generation_time_seconds,
        )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "lesson_id": 1,
                "script": [
                    {"type": "speak", "content": "Welcome back to Senda..."},
                    {"type": "pause", "duration": 3.0},
                ],
                "generation_time_seconds": 2.45,
            }
        }


class CourseScriptsGenerationResponse(BaseModel):
    """Response for bulk course script generation."""

    generated_scripts: list[ScriptGenerationResponse] = Field(
        ..., description="List of generated script results"
    )
    total_lessons_processed: int = Field(
        ..., description="Total number of lessons that were requested for processing"
    )
    successful_generations: int = Field(
        ..., description="Number of successful script generations"
    )
    errors: list["GenerationErrorResponse"] = Field(
        default_factory=list, description="List of errors for failed generations"
    )

    @classmethod
    def from_batch_result(
        cls, batch_result: "BatchScriptGenerationResultDTO"
    ) -> "CourseScriptsGenerationResponse":
        """Create response from batch generation result DTO."""

        return cls(
            generated_scripts=[
                ScriptGenerationResponse.from_dto(dto) for dto in batch_result.results
            ],
            total_lessons_processed=batch_result.total_requested,
            successful_generations=len(batch_result.results),
            errors=[
                GenerationErrorResponse(
                    lesson_id=error.lesson_id,
                    error_type=error.error_type,
                    error_message=error.error_message,
                )
                for error in batch_result.errors
            ],
        )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "generated_scripts": [
                    {
                        "lesson_id": 1,
                        "script": [
                            {"type": "speak", "content": "Welcome back to Senda..."}
                        ],
                        "generation_time_seconds": 2.45,
                    }
                ],
                "total_lessons_processed": 3,
                "successful_generations": 1,
                "errors": [
                    {
                        "lesson_id": 2,
                        "error_type": "ScriptGenerationException",
                        "error_message": "AI provider timeout",
                    }
                ],
            }
        }


class GenerationErrorResponse(BaseModel):
    """Error details for a failed generation attempt."""

    lesson_id: int = Field(..., description="ID of the lesson that failed")
    error_type: str = Field(..., description="Type/class of the error")
    error_message: str = Field(..., description="Human-readable error message")


class ScriptGenerationStatusResponse(BaseModel):
    """Response for script generation status check."""

    lesson_id: int = Field(..., description="ID of the lesson")
    status: str = Field(..., description="Current generation status")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {"example": {"lesson_id": 1, "status": "SCRIPT_GENERATING"}}
