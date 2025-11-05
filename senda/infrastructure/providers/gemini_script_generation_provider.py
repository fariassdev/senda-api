"""Gemini AI implementation of lesson script generation provider."""

import json
import logging

from google import genai
from google.genai import errors, types

from senda.api.schemas.responses.script_schemas import GeminiScriptSchema
from senda.core.exceptions import (
    AIProviderUnavailableException,
    InvalidPromptException,
    ScriptGenerationException,
)
from senda.domain.dtos.script_generation import (
    CourseContextDTO,
    LessonContextDTO,
    ScriptPartDTO,
)
from senda.domain.services.script_generation import ILessonScriptProvider
from senda.infrastructure.config.gemini_config import GeminiConfig
from senda.infrastructure.loaders.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class GeminiLessonScriptProvider(ILessonScriptProvider):
    """
    Gemini AI implementation of the lesson script generation provider.
    Uses Gemini schemas from API layer for structured output.
    """

    SYSTEM_PROMPT_PATH = "senda/infrastructure/prompts/lesson_script_system.md"

    def __init__(self, config: GeminiConfig, prompt_loader: PromptLoader):
        self._config = config
        self._prompt_loader = prompt_loader
        self._client = genai.Client(api_key=config.api_key)
        self._system_instruction = self._load_system_instruction()

    async def generate_script(
        self, course_context: CourseContextDTO, lesson_context: LessonContextDTO
    ) -> list[ScriptPartDTO]:
        """Generates lesson script using Gemini API with structured schema."""
        try:
            logger.info(
                f"Generating script for lesson {lesson_context.lesson_number}: "
                f"'{lesson_context.title}'"
            )

            enhanced_prompt = self._build_lesson_prompt(course_context, lesson_context)
            gemini_response = await self._call_gemini_api(enhanced_prompt)

            script_parts = gemini_schema_to_script_parts(gemini_response)

            logger.info(
                f"Generated script for lesson '{lesson_context.title}' "
                f"with {len(script_parts)} parts"
            )

            return script_parts

        except errors.APIError as e:
            logger.error(f"Gemini API error: {e.code} - {e.message}")

            if e.code == 400:
                raise InvalidPromptException(
                    message=f"Invalid lesson context: {e.message}"
                ) from e
            elif e.code == 429:
                raise AIProviderUnavailableException(
                    message="Rate limit exceeded. Please try again later."
                ) from e
            elif e.code in (503, 504):
                raise AIProviderUnavailableException(
                    message="Gemini service unavailable"
                ) from e
            elif e.code == 408:
                raise ScriptGenerationException(
                    message="Script generation timed out"
                ) from e
            else:
                raise ScriptGenerationException(
                    message=f"Script generation failed: {e.message}"
                ) from e

        except Exception as e:
            logger.exception(f"Unexpected error during script generation: {e}")
            raise ScriptGenerationException(
                message=f"Script generation failed: {str(e)}"
            ) from e

    def _build_lesson_prompt(
        self, course_context: CourseContextDTO, lesson_context: LessonContextDTO
    ) -> str:
        """Builds the lesson script generation prompt with context."""
        prompt_data = {
            "courseContext": {
                "name": course_context.name,
                "description": course_context.description,
                "totalLessons": course_context.total_lessons,
            },
            "lessonDetails": {
                "lessonNumber": lesson_context.lesson_number,
                "title": lesson_context.title,
                "corePractice": lesson_context.core_practice,
                "durationMinutes": lesson_context.duration_minutes,
                "keyPoint": lesson_context.key_point,
                "tone": lesson_context.tone,
            },
        }

        return json.dumps(prompt_data, indent=2)

    async def _call_gemini_api(self, prompt: str) -> GeminiScriptSchema:
        """Calls Gemini API with structured Pydantic schema output."""
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        ]

        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_budget=self._config.thinking_budget
            ),
            response_mime_type="application/json",
            response_schema=GeminiScriptSchema,
            system_instruction=self._system_instruction,
        )

        response = self._client.models.generate_content(
            model=self._config.model, contents=contents, config=config
        )

        return response.parsed

    def _load_system_instruction(self) -> list[types.Part]:
        """Loads system instruction from file using the class constant path."""
        prompt_text = self._prompt_loader.load_prompt(self.SYSTEM_PROMPT_PATH)
        return [types.Part.from_text(text=prompt_text)]


def gemini_schema_to_script_parts(schema: GeminiScriptSchema) -> list[ScriptPartDTO]:
    """
    Maps Gemini API schema to domain DTOs.

    Args:
        schema: GeminiScriptSchema from Gemini API response

    Returns:
        List of ScriptPartDTO for domain layer
    """
    return [
        ScriptPartDTO(type=part.type, content=part.content, duration=part.duration)
        for part in schema.script
    ]
