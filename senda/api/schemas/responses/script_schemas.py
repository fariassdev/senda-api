"""Gemini-specific response schemas for lesson script generation."""

from pydantic import BaseModel, Field

from senda.core.enums import ScriptPartType


class GeminiScriptPartSchema(BaseModel):
    """Schema for individual script parts in Gemini API response."""

    type: ScriptPartType = Field(
        ..., description="Type of script part (speak or pause)"
    )
    content: str | None = Field(
        None, description="Content text for speak parts, null for pause parts"
    )
    duration: float | None = Field(
        None, description="Duration in seconds for pause parts, optional for speak"
    )


class GeminiScriptSchema(BaseModel):
    """Complete script response schema from Gemini API."""

    script: list[GeminiScriptPartSchema] = Field(
        ..., description="List of script parts forming the complete meditation script"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "script": [
                    {"type": "speak", "content": "Welcome back to Senda..."},
                    {"type": "pause", "duration": 3.0},
                    {
                        "type": "speak",
                        "content": "Let's begin by finding a comfortable position...",
                    },
                ]
            }
        }
