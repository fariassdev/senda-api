"""Abstract interfaces for lesson script generation services."""

import abc

from senda.domain.dtos.script_generation import (
    CourseContextDTO,
    CourseScriptRequestDTO,
    LessonContextDTO,
    LessonScriptRequestDTO,
    ScriptGenerationResultDTO,
    ScriptPartDTO,
)


class ILessonScriptProvider(abc.ABC):
    """Abstract interface for AI-powered lesson script generation."""

    @abc.abstractmethod
    async def generate_script(
        self, course_context: CourseContextDTO, lesson_context: LessonContextDTO
    ) -> list[ScriptPartDTO]:
        """
        Generates a meditation script for a specific lesson within a course.

        Args:
            course_context: Context about the course (name, description, total lessons)
            lesson_context: Details about the specific lesson

        Returns:
            List of ScriptPartDTO representing the generated meditation script

        Raises:
            ScriptGenerationException: If generation fails
            InvalidPromptException: If lesson context violates content policy
        """
        pass


class IScriptGenerationService(abc.ABC):
    """Abstract interface for script generation business logic."""

    @abc.abstractmethod
    async def generate_lesson_script(
        self, session: object, request: LessonScriptRequestDTO
    ) -> ScriptGenerationResultDTO:
        """
        Generate and save a script for a single lesson.

        Args:
            session: Database session
            request: Lesson script generation request

        Returns:
            ScriptGenerationResultDTO with generated script

        Raises:
            LessonNotFoundException: If lesson not found
            ScriptGenerationException: If generation fails
        """
        pass

    @abc.abstractmethod
    async def generate_course_scripts(
        self, session: object, request: CourseScriptRequestDTO
    ) -> list[ScriptGenerationResultDTO]:
        """
        Generate scripts for all ungenerated lessons in a course.

        Args:
            session: Database session
            request: Course script generation request

        Returns:
            List of ScriptGenerationResultDTO for all generated lessons

        Raises:
            CourseNotFoundException: If course not found
            ScriptGenerationException: If generation fails
        """
        pass

    @abc.abstractmethod
    async def get_lesson_generation_status(
        self, session: object, lesson_id: int, user_id: int
    ) -> str:
        """
        Get the current generation status of a lesson script.

        Args:
            session: Database session
            lesson_id: ID of the lesson
            user_id: ID of the requesting user

        Returns:
            Current lesson status (PENDING, SCRIPT_GENERATING, etc.)

        Raises:
            LessonNotFoundException: If lesson not found
        """
        pass
