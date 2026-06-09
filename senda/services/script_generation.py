"""Script generation service implementing business logic for lesson script generation."""

import logging
import time
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from senda.core.enums import LessonStatus
from senda.core.exceptions import (
    CourseNotFoundException,
    LessonNotFoundException,
    ScriptGenerationException,
)
from senda.domain.dtos.lesson import UpdateLessonDTO
from senda.domain.dtos.script_generation import (
    BatchScriptGenerationResultDTO,
    CourseContextDTO,
    CourseScriptRequestDTO,
    GenerationErrorDTO,
    LessonContextDTO,
    LessonScriptRequestDTO,
    ScriptGenerationResultDTO,
    StartScriptGenerationResultDTO,
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
        session_factory: async_sessionmaker[AsyncSession],
        script_provider: ILessonScriptProvider | None = None,
    ) -> None:
        self._course_repo = course_repo
        self._lesson_repo = lesson_repo
        self._script_provider = script_provider
        self._session_factory = session_factory

    async def start_script_generation(
        self, session: AsyncSession, lesson_id: int
    ) -> StartScriptGenerationResultDTO:
        """
        Validate and set status to SCRIPT_GENERATING, or return an in-flight job.
        """
        lesson_record = await self._lesson_repo.get_or_none(
            session=session, lesson_id=lesson_id
        )
        if not lesson_record:
            raise LessonNotFoundException()

        if lesson_record.status == LessonStatus.SCRIPT_GENERATING:
            logger.info(
                "Returning existing in-flight script generation for lesson %s",
                lesson_id,
            )
            return StartScriptGenerationResultDTO(
                lesson_id=lesson_id, status=lesson_record.status, is_new=False
            )

        await self._lesson_repo.update(
            session=session,
            lesson_id=lesson_id,
            update_item=UpdateLessonDTO(status=LessonStatus.SCRIPT_GENERATING),
        )

        return StartScriptGenerationResultDTO(
            lesson_id=lesson_id,
            status=LessonStatus.SCRIPT_GENERATING.value,
            is_new=True,
        )

    async def run_script_generation(self, lesson_id: int, user_id: int) -> None:
        """
        Run the script generation pipeline in the background using a fresh database session.
        """
        async with self._session_factory() as session:
            try:
                await self._execute_script_generation(
                    session=session, lesson_id=lesson_id
                )
            except Exception as exc:
                logger.exception(
                    "Background script generation failed for lesson %s: %s",
                    lesson_id,
                    exc,
                )
                await self._ensure_script_failed(session=session, lesson_id=lesson_id)

    async def generate_lesson_script(
        self, session: AsyncSession, request: LessonScriptRequestDTO
    ) -> ScriptGenerationResultDTO:
        """
        Generate and save a script for a single lesson.

        Raises:
            LessonNotFoundException: If lesson not found
            ScriptGenerationException: If generation fails or provider not configured
        """
        lesson_record = await self._lesson_repo.get_or_none(
            session=session, lesson_id=request.lesson_id
        )
        if not lesson_record:
            raise LessonNotFoundException()

        await self._lesson_repo.update(
            session=session,
            lesson_id=request.lesson_id,
            update_item=UpdateLessonDTO(status=LessonStatus.SCRIPT_GENERATING),
        )

        return await self._execute_script_generation(
            session=session, lesson_id=request.lesson_id
        )

    async def _execute_script_generation(
        self, session: AsyncSession, lesson_id: int
    ) -> ScriptGenerationResultDTO:
        """
        Generate and persist a lesson script.

        Assumes the lesson is already in SCRIPT_GENERATING state.
        """
        logger.info("Starting script generation for lesson %s", lesson_id)
        start_time = time.time()

        try:
            if not self._script_provider:
                raise ScriptGenerationException(
                    message="Script generation provider not configured"
                )

            lesson_record = await self._lesson_repo.get_or_none(
                session=session, lesson_id=lesson_id
            )
            if not lesson_record:
                raise LessonNotFoundException()

            course_record = await self._course_repo.get_by_id(
                session=session, course_id=lesson_record.course_id
            )
            if not course_record:
                raise CourseNotFoundException()

            total_lessons = await self._lesson_repo.count(
                session=session, course_id=course_record.id
            )

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

            script_parts = await self._script_provider.generate_script(
                course_context=course_context, lesson_context=lesson_context
            )

            await self._lesson_repo.update(
                session=session,
                lesson_id=lesson_id,
                update_item=UpdateLessonDTO(
                    script=script_parts,
                    status=LessonStatus.SCRIPT_COMPLETED,
                    script_generated_at=datetime.now(),
                ),
            )

            generation_time = time.time() - start_time
            logger.info(
                "Successfully generated script for lesson %s in %.2f seconds",
                lesson_id,
                generation_time,
            )

            return ScriptGenerationResultDTO(
                lesson_id=lesson_id,
                script=script_parts,
                generation_time_seconds=generation_time,
            )

        except (
            LessonNotFoundException,
            CourseNotFoundException,
            ScriptGenerationException,
        ):
            await self._mark_script_failed(session=session, lesson_id=lesson_id)
            raise

        except Exception as exc:
            logger.exception(
                "Unexpected error generating script for lesson %s: %s", lesson_id, exc
            )
            await self._mark_script_failed(session=session, lesson_id=lesson_id)
            raise ScriptGenerationException(
                message=f"Script generation failed: {str(exc)}"
            ) from exc

    async def _mark_script_failed(self, session: AsyncSession, lesson_id: int) -> None:
        await self._lesson_repo.update(
            session=session,
            lesson_id=lesson_id,
            update_item=UpdateLessonDTO(status=LessonStatus.SCRIPT_FAILED),
        )

    async def _ensure_script_failed(
        self, session: AsyncSession, lesson_id: int
    ) -> None:
        lesson_record = await self._lesson_repo.get_or_none(
            session=session, lesson_id=lesson_id
        )
        if lesson_record is None:
            return
        if lesson_record.status != LessonStatus.SCRIPT_GENERATING:
            return

        await self._mark_script_failed(session=session, lesson_id=lesson_id)

    async def generate_course_scripts(
        self, session: AsyncSession, request: CourseScriptRequestDTO
    ) -> BatchScriptGenerationResultDTO:
        """
        Generate scripts for lessons in a course.

        Args:
            session: Database session
            request: Request with slug and optional lesson_ids
                - If lesson_ids is None: generate for all eligible lessons
                - If lesson_ids is []: generate nothing (return empty result)
                - If lesson_ids is [1, 2, 3]: generate only for those specific lessons

        Returns:
            BatchScriptGenerationResultDTO with successful results and any errors

        Raises:
            CourseNotFoundException: If course not found
            ScriptGenerationException: If provider not configured
        """
        if not self._script_provider:
            raise ScriptGenerationException(
                message="Script generation provider not configured"
            )

        # Handle empty array case - explicit request to generate nothing
        if request.lesson_ids is not None and len(request.lesson_ids) == 0:
            logger.info(
                f"Empty lesson_ids provided for course {request.slug} - skipping generation"
            )
            return BatchScriptGenerationResultDTO(
                results=[], errors=[], total_requested=0
            )

        logger.info(f"Starting bulk script generation for course {request.slug}")

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

        # If specific lesson_ids provided, filter to only those lessons
        if request.lesson_ids is not None:
            ungenerated_lessons = [
                lesson
                for lesson in ungenerated_lessons
                if lesson.id in request.lesson_ids
            ]
            logger.info(
                f"Filtered to {len(ungenerated_lessons)} lessons based on provided IDs"
            )

        if not ungenerated_lessons:
            logger.info(f"No ungenerated lessons found for course {request.slug}")
            return BatchScriptGenerationResultDTO(
                results=[], errors=[], total_requested=0
            )

        logger.info(
            f"Found {len(ungenerated_lessons)} ungenerated lessons for course {request.slug}"
        )

        generated_results: list[ScriptGenerationResultDTO] = []
        generation_errors: list[GenerationErrorDTO] = []

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
                error_type = type(e).__name__
                error_message = str(e)
                logger.error(
                    f"Failed to generate script for lesson {lesson_record.id}: {e}"
                )
                generation_errors.append(
                    GenerationErrorDTO(
                        lesson_id=lesson_record.id,
                        error_type=error_type,
                        error_message=error_message,
                    )
                )
                # Continue with other lessons even if one fails

        logger.info(
            f"Completed bulk generation for course {request.slug}: "
            f"{len(generated_results)}/{len(ungenerated_lessons)} successful, "
            f"{len(generation_errors)} errors"
        )

        return BatchScriptGenerationResultDTO(
            results=generated_results,
            errors=generation_errors,
            total_requested=len(ungenerated_lessons),
        )

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
