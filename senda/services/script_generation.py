"""Script generation service implementing business logic for lesson script generation."""

import logging
import time
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.enums import LessonStatus
from senda.core.exceptions import (
    CourseNotFoundException,
    LessonNotFoundException,
    ScriptGenerationException,
)
from senda.domain.dtos.lesson import UpdateLessonDTO
from senda.domain.dtos.script_generation import (
    CourseContextDTO,
    CourseScriptRequestDTO,
    LessonContextDTO,
    LessonScriptRequestDTO,
    ScriptGenerationResultDTO,
)
from senda.domain.repositories.course import ICourseRepository
from senda.domain.repositories.lesson import ILessonRepository
from senda.domain.services.script_generation import (
    ILessonScriptProvider,
    IScriptGenerationService,
)

logger = logging.getLogger(__name__)


class ScriptGenerationService(IScriptGenerationService):
    """Service to handle lesson script generation logic."""

    def __init__(
        self,
        course_repo: ICourseRepository,
        lesson_repo: ILessonRepository,
        script_provider: ILessonScriptProvider | None = None,
    ) -> None:
        self._course_repo = course_repo
        self._lesson_repo = lesson_repo
        self._script_provider = script_provider

    async def generate_lesson_script(
        self, session: AsyncSession, request: LessonScriptRequestDTO
    ) -> ScriptGenerationResultDTO:
        """
        Generate and save a script for a single lesson.

        Raises:
            LessonNotFoundException: If lesson not found
            ScriptGenerationException: If generation fails or provider not configured
        """
        if not self._script_provider:
            raise ScriptGenerationException(
                message="Script generation provider not configured"
            )

        logger.info(f"Starting script generation for lesson {request.lesson_id}")
        start_time = time.time()

        try:
            # Get lesson and validate permissions
            lesson_record = await self._lesson_repo.get_or_none(
                session=session, lesson_id=request.lesson_id
            )
            if not lesson_record:
                raise LessonNotFoundException()

            # Get course context
            course_record = await self._course_repo.get_by_id(
                session=session, course_id=lesson_record.course_id
            )
            if not course_record:
                raise CourseNotFoundException()

            # Update lesson status to generating
            await self._lesson_repo.update(
                session=session,
                lesson_id=request.lesson_id,
                update_item=UpdateLessonDTO(status=LessonStatus.SCRIPT_GENERATING),
            )

            # Get total lesson count for course context
            total_lessons = await self._lesson_repo.count(
                session=session, course_id=course_record.id
            )

            # Prepare context data
            course_context = CourseContextDTO(
                name=course_record.title,
                description=course_record.description,
                total_lessons=total_lessons,
            )

            lesson_context = LessonContextDTO(
                lesson_number=lesson_record.lesson_number,
                title=lesson_record.title,
                core_practice=lesson_record.core_practice,
                duration_minutes=lesson_record.duration_minutes,
                key_point=lesson_record.key_point,
                tone=lesson_record.tone,
            )

            # Generate script using AI provider
            script_parts = await self._script_provider.generate_script(
                course_context=course_context, lesson_context=lesson_context
            )

            # Save script and update status
            await self._lesson_repo.update(
                session=session,
                lesson_id=request.lesson_id,
                update_item=UpdateLessonDTO(
                    script=script_parts,
                    status=LessonStatus.SCRIPT_COMPLETED,
                    script_generated_at=datetime.now(),
                ),
            )

            generation_time = time.time() - start_time
            logger.info(
                f"Successfully generated script for lesson {request.lesson_id} "
                f"in {generation_time:.2f} seconds"
            )

            return ScriptGenerationResultDTO(
                lesson_id=request.lesson_id,
                script=script_parts,
                generation_time_seconds=generation_time,
            )

        except (
            LessonNotFoundException,
            CourseNotFoundException,
            ScriptGenerationException,
        ):
            # Update status to failed and re-raise known exceptions
            await self._lesson_repo.update(
                session=session,
                lesson_id=request.lesson_id,
                update_item=UpdateLessonDTO(status=LessonStatus.SCRIPT_FAILED),
            )
            raise

        except Exception as e:
            # Update status to failed for unexpected errors
            logger.exception(
                f"Unexpected error generating script for lesson {request.lesson_id}: {e}"
            )
            await self._lesson_repo.update(
                session=session,
                lesson_id=request.lesson_id,
                update_item=UpdateLessonDTO(status=LessonStatus.SCRIPT_FAILED),
            )
            raise ScriptGenerationException(
                message=f"Script generation failed: {str(e)}"
            ) from e

    async def generate_course_scripts(
        self, session: AsyncSession, request: CourseScriptRequestDTO
    ) -> list[ScriptGenerationResultDTO]:
        """
        Generate scripts for all ungenerated lessons in a course.

        Raises:
            CourseNotFoundException: If course not found
            ScriptGenerationException: If generation fails
        """
        if not self._script_provider:
            raise ScriptGenerationException(
                message="Script generation provider not configured"
            )

        logger.info(f"Starting bulk script generation for course {request.course_id}")

        # Get course and validate permissions
        course_record = await self._course_repo.get_by_slug(
            session=session, slug=request.slug
        )

        # Get all lessons for the course and filter ungenerated ones
        all_lessons = await self._lesson_repo.list_by_course(
            session=session, course_id=course_record.id
        )

        # Filter lessons that don't have generated scripts
        ungenerated_lessons = [
            lesson
            for lesson in all_lessons
            if lesson.status in [LessonStatus.PENDING, LessonStatus.SCRIPT_FAILED]
            or lesson.script is None
        ]

        if not ungenerated_lessons:
            logger.info(f"No ungenerated lessons found for course {request.course_id}")
            return []

        logger.info(
            f"Found {len(ungenerated_lessons)} ungenerated lessons for course {request.course_id}"
        )

        generated_results: list[ScriptGenerationResultDTO] = []

        for lesson_record in ungenerated_lessons:
            lesson_request = LessonScriptRequestDTO(
                lesson_id=lesson_record.id, user_id=request.user_id
            )

            try:
                result = await self.generate_lesson_script(
                    session=session, request=lesson_request
                )
                generated_results.append(result)
                logger.info(f"Generated script for lesson {lesson_record.id}")

            except Exception as e:
                logger.error(
                    f"Failed to generate script for lesson {lesson_record.id}: {e}"
                )
                # Continue with other lessons even if one fails

        logger.info(
            f"Completed bulk generation for course {request.course_id}: "
            f"{len(generated_results)}/{len(ungenerated_lessons)} successful"
        )

        return generated_results

    async def get_lesson_generation_status(
        self, session: AsyncSession, lesson_id: int, user_id: int
    ) -> str:
        """
        Get the current generation status of a lesson script.

        Raises:
            LessonNotFoundException: If lesson not found
        """
        lesson_record = await self._lesson_repo.get_or_none(
            session=session, lesson_id=lesson_id
        )
        if not lesson_record:
            raise LessonNotFoundException()

        # Get course to check permissions
        course_record = await self._course_repo.get_by_id(
            session=session, course_id=lesson_record.course_id
        )
        if not course_record:
            raise CourseNotFoundException()

        return lesson_record.status
