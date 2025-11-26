"""Gemini AI implementation of course generation provider."""

import logging

from google import genai
from google.genai import errors, types

from senda.api.schemas.responses.gemini_schemas import GeminiCourseSchema
from senda.core.enums import DifficultyLevel
from senda.core.exceptions import (
    AIProviderUnavailableException,
    CourseGenerationException,
    InvalidPromptException,
)
from senda.domain.dtos.course_generation import (
    CourseGenerationRequestDTO,
    CourseStructureDTO,
    LessonStructureDTO,
)
from senda.domain.services.course import ICourseGenerationProvider
from senda.infrastructure.config.gemini_config import GeminiConfig
from senda.infrastructure.loaders.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class GeminiCourseGenerationProvider(ICourseGenerationProvider):
    """
    Gemini AI implementation of the course generation provider.
    Uses Gemini schemas from API layer for structured output.
    """

    SYSTEM_PROMPT_PATH = "senda/infrastructure/prompts/course_architect_system.md"

    def __init__(self, config: GeminiConfig, prompt_loader: PromptLoader):
        self._config = config
        self._prompt_loader = prompt_loader
        self._client = genai.Client(api_key=config.api_key)
        self._system_instruction = self._load_system_instruction()

    async def generate_course_structure(
        self, request: CourseGenerationRequestDTO
    ) -> CourseStructureDTO:
        """Generates course structure using Gemini API with structured schema."""
        try:
            logger.info(
                f"Generating course for user {request.user_id}: "
                f"'{request.prompt[:100]}...'"
            )

            enhanced_prompt = self._build_enhanced_prompt(request)
            gemini_response = await self._call_gemini_api(enhanced_prompt)

            course_structure = gemini_schema_to_structure_dto(gemini_response)

            logger.info(
                f"Generated course '{course_structure.title}' "
                f"with {len(course_structure.lessons)} lessons"
            )

            return course_structure

        except errors.APIError as e:
            logger.error(f"Gemini API error: {e.code} - {e.message}")

            if e.code == 400:
                raise InvalidPromptException(
                    message=f"Invalid prompt: {e.message}"
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
                raise CourseGenerationException(
                    message="Course generation timed out"
                ) from e
            else:
                raise CourseGenerationException(
                    message=f"Course generation failed: {e.message}"
                ) from e

        except Exception as e:
            logger.exception(f"Unexpected error during course generation: {e}")
            raise CourseGenerationException(
                message=f"Course generation failed: {str(e)}"
            ) from e

    def _build_enhanced_prompt(self, request: CourseGenerationRequestDTO) -> str:
        """Builds the final prompt with optional constraints."""
        parts = [request.prompt]

        if request.difficulty_level:
            parts.append(f"Difficulty level: {request.difficulty_level.value}")

        return "\n".join(parts)

    async def _call_gemini_api(self, prompt: str) -> GeminiCourseSchema:
        """Calls Gemini API with structured Pydantic schema output."""
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        ]

        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_budget=self._config.thinking_budget
            ),
            response_mime_type="application/json",
            response_schema=GeminiCourseSchema,
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


def gemini_schema_to_structure_dto(schema: GeminiCourseSchema) -> CourseStructureDTO:
    """
    Maps Gemini API schema to domain DTO.

    Args:
        schema: GeminiCourseSchema from Gemini API response

    Returns:
        CourseStructureDTO for domain layer
    """
    lessons = [
        LessonStructureDTO(
            title=lesson.title,
            core_practice=lesson.core_practice,
            key_point=lesson.key_point,
            tone=lesson.tone,
            duration_minutes=lesson.duration_minutes,
            order=lesson.order,
        )
        for lesson in schema.lessons
    ]

    return CourseStructureDTO(
        title=schema.title,
        description=schema.description,
        duration_days=schema.duration_days,
        difficulty_level=schema.difficulty_level,
        tags=schema.tags,
        lessons=lessons,
    )
