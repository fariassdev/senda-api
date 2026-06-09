"""Integration tests for script generation API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from senda.core.enums import LessonStatus
from senda.domain.dtos.script_generation import StartScriptGenerationResultDTO


class TestScriptGenerationAPI:
    """Test suite for async lesson script generation endpoints."""

    @pytest.mark.anyio
    async def test_generate_lesson_script_success(
        self, admin_test_client: AsyncClient, admin_user, test_course, session
    ):
        """Async script generation returns 202 with SCRIPT_GENERATING status."""
        from senda.infrastructure.models import Course, Lesson

        course = await session.get(Course, test_course.id)
        lesson = Lesson(
            course_id=course.id,
            lesson_number=1,
            title="Test Lesson",
            core_practice="Breathing",
            key_point="Focus",
            tone="calm",
            duration_minutes=10,
            status=LessonStatus.PENDING,
            created_at=datetime.now(),
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        lesson_id = lesson.id

        mock_result = StartScriptGenerationResultDTO(
            lesson_id=lesson_id,
            status=LessonStatus.SCRIPT_GENERATING.value,
            is_new=True,
        )

        with (
            patch(
                "senda.services.script_generation.ScriptGenerationService.start_script_generation",
                new_callable=AsyncMock,
                return_value=mock_result,
            ) as mock_start,
            patch(
                "senda.services.script_generation.ScriptGenerationService.run_script_generation",
                new_callable=AsyncMock,
            ) as mock_run,
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/lessons/{lesson_id}/generate-script"
            )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["lesson_id"] == lesson_id
        assert data["status"] == LessonStatus.SCRIPT_GENERATING.value
        mock_start.assert_awaited_once()
        mock_run.assert_awaited_once_with(lesson_id, admin_user.id)

    @pytest.mark.anyio
    async def test_generate_lesson_script_idempotent_skips_background_task(
        self, admin_test_client: AsyncClient, test_course, session
    ):
        """Duplicate requests while generating do not enqueue another background run."""
        from senda.infrastructure.models import Course, Lesson

        course = await session.get(Course, test_course.id)
        lesson = Lesson(
            course_id=course.id,
            lesson_number=1,
            title="Generating Lesson",
            core_practice="Breathing",
            key_point="Focus",
            tone="calm",
            duration_minutes=10,
            status=LessonStatus.SCRIPT_GENERATING,
            created_at=datetime.now(),
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        lesson_id = lesson.id

        mock_result = StartScriptGenerationResultDTO(
            lesson_id=lesson_id,
            status=LessonStatus.SCRIPT_GENERATING.value,
            is_new=False,
        )

        with (
            patch(
                "senda.services.script_generation.ScriptGenerationService.start_script_generation",
                new_callable=AsyncMock,
                return_value=mock_result,
            ),
            patch(
                "senda.services.script_generation.ScriptGenerationService.run_script_generation",
                new_callable=AsyncMock,
            ) as mock_run,
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/lessons/{lesson_id}/generate-script"
            )

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["status"] == LessonStatus.SCRIPT_GENERATING.value
        mock_run.assert_not_called()

    @pytest.mark.anyio
    async def test_generate_lesson_script_lesson_not_found(
        self, admin_test_client: AsyncClient, test_course
    ):
        """Missing lesson returns 404."""
        from senda.core.exceptions import LessonNotFoundException

        with patch(
            "senda.services.script_generation.ScriptGenerationService.start_script_generation",
            new_callable=AsyncMock,
            side_effect=LessonNotFoundException(),
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/lessons/99999/generate-script"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_generate_lesson_script_unauthorized(
        self, test_client: AsyncClient, test_course
    ):
        """Unauthenticated access is rejected."""
        response = await test_client.post(
            f"/courses/{test_course.slug}/lessons/1/generate-script"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.anyio
    async def test_generate_lesson_script_user_not_admin(
        self, authorized_test_client: AsyncClient, test_course
    ):
        """Non-admin users cannot start script generation."""
        response = await authorized_test_client.post(
            f"/courses/{test_course.slug}/lessons/1/generate-script"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
