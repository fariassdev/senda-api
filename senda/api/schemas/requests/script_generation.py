"""Request schemas for script generation API endpoints."""

from pydantic import BaseModel, Field


class GenerateScriptRequest(BaseModel):
    """Request to generate script for a lesson."""

    lesson_id: int = Field(..., description="ID of the lesson to generate script for")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {"example": {"lesson_id": 1}}


class GenerateCourseScriptsRequest(BaseModel):
    """Request to generate scripts for all lessons in a course."""

    # The course is identified by the slug in the URL path
    # No additional fields needed in the request body
    pass
