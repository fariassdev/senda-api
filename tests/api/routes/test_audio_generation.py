"""Integration tests for audio generation API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from senda.core.enums import LessonStatus
from senda.domain.dtos.audio_generation import AudioGenerationResultDTO


class TestAudioGenerationAPI:
    """Test suite for audio generation endpoints."""

    @pytest.mark.anyio
    async def test_generate_lesson_audio_success(
        self, authorized_test_client: AsyncClient, test_user, test_course, session
    ):
        """Test successful lesson audio generation."""
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
            status=LessonStatus.SCRIPT_COMPLETED,
            script='[{"type": "speak", "content": "Hello"}]',
            created_at=datetime.now(),
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        lesson_id = lesson.id

        mock_result = AudioGenerationResultDTO(
            lesson_id=lesson_id,
            audio_url="https://s3.amazonaws.com/audio/test.mp3",
            generation_time_seconds=5.0,
            file_size_bytes=1024,
        )

        with patch(
            "senda.services.audio_generation.AudioGenerationService.generate_lesson_audio",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = await authorized_test_client.post(
                f"/courses/{test_course.slug}/lessons/{lesson_id}/generate-audio"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["lesson_id"] == lesson_id
        assert data["audio_url"] == "https://s3.amazonaws.com/audio/test.mp3"
        assert data["generation_time_seconds"] == 5.0
        assert data["file_size_bytes"] == 1024

    @pytest.mark.anyio
    async def test_generate_lesson_audio_unauthorized(
        self, test_client: AsyncClient, test_course
    ):
        """Test unauthorized access is rejected."""
        response = await test_client.post(
            f"/courses/{test_course.slug}/lessons/1/generate-audio"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.anyio
    async def test_generate_lesson_audio_lesson_not_found(
        self, authorized_test_client: AsyncClient, test_course
    ):
        """Test error when lesson does not exist."""
        from senda.core.exceptions import LessonNotFoundException

        with patch(
            "senda.services.audio_generation.AudioGenerationService.generate_lesson_audio",
            new_callable=AsyncMock,
            side_effect=LessonNotFoundException(),
        ):
            response = await authorized_test_client.post(
                f"/courses/{test_course.slug}/lessons/99999/generate-audio"
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_generate_lesson_audio_invalid_state(
        self, authorized_test_client: AsyncClient, test_course, session
    ):
        """Test error when lesson is not ready for audio generation."""
        from senda.core.exceptions import InvalidLessonStateException
        from senda.infrastructure.models import Course, Lesson

        course = await session.get(Course, test_course.id)
        lesson = Lesson(
            course_id=course.id,
            lesson_number=1,
            title="Pending Lesson",
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

        with patch(
            "senda.services.audio_generation.AudioGenerationService.generate_lesson_audio",
            new_callable=AsyncMock,
            side_effect=InvalidLessonStateException(),
        ):
            response = await authorized_test_client.post(
                f"/courses/{test_course.slug}/lessons/{lesson_id}/generate-audio"
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.anyio
    async def test_generate_course_audios_success(
        self, authorized_test_client: AsyncClient, test_user, test_course, session
    ):
        """Test successful bulk audio generation for course."""
        from senda.infrastructure.models import Course, Lesson

        course = await session.get(Course, test_course.id)

        lesson1 = Lesson(
            course_id=course.id,
            lesson_number=1,
            title="Lesson 1",
            core_practice="Breathing",
            key_point="Focus",
            tone="calm",
            duration_minutes=10,
            status=LessonStatus.SCRIPT_COMPLETED,
            script='[{"type": "speak", "content": "Hello"}]',
            created_at=datetime.now(),
        )
        lesson2 = Lesson(
            course_id=course.id,
            lesson_number=2,
            title="Lesson 2",
            core_practice="Awareness",
            key_point="Observe",
            tone="calm",
            duration_minutes=10,
            status=LessonStatus.SCRIPT_COMPLETED,
            script='[{"type": "speak", "content": "World"}]',
            created_at=datetime.now(),
        )
        session.add_all([lesson1, lesson2])
        await session.commit()
        await session.refresh(lesson1)
        await session.refresh(lesson2)
        lesson1_id = lesson1.id
        lesson2_id = lesson2.id

        mock_results = [
            AudioGenerationResultDTO(
                lesson_id=lesson1_id,
                audio_url="https://s3.amazonaws.com/audio/lesson1.mp3",
                generation_time_seconds=5.0,
                file_size_bytes=1024,
            ),
            AudioGenerationResultDTO(
                lesson_id=lesson2_id,
                audio_url="https://s3.amazonaws.com/audio/lesson2.mp3",
                generation_time_seconds=6.0,
                file_size_bytes=2048,
            ),
        ]

        with patch(
            "senda.services.audio_generation.AudioGenerationService.generate_course_audios",
            new_callable=AsyncMock,
            return_value=mock_results,
        ):
            response = await authorized_test_client.post(
                f"/courses/{test_course.slug}/generate-all-audios"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "generated_audios" in data
        generated_audios = data["generated_audios"]
        assert "total_lessons_processed" in data
        assert data["total_lessons_processed"] == 2
        assert len(generated_audios) == 2

        assert generated_audios[0]["lesson_id"] == lesson1_id
        assert (
            generated_audios[0]["audio_url"]
            == "https://s3.amazonaws.com/audio/lesson1.mp3"
        )
        assert generated_audios[1]["lesson_id"] == lesson2_id
        assert (
            generated_audios[1]["audio_url"]
            == "https://s3.amazonaws.com/audio/lesson2.mp3"
        )

    @pytest.mark.anyio
    async def test_generate_course_audios_unauthorized(
        self, test_client: AsyncClient, test_course
    ):
        """Test unauthorized access is rejected."""
        response = await test_client.post(
            f"/courses/{test_course.slug}/generate-all-audios"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.anyio
    async def test_generate_course_audios_no_ready_lessons(
        self, authorized_test_client: AsyncClient, test_course
    ):
        """Test bulk generation when no lessons are ready."""
        with patch(
            "senda.services.audio_generation.AudioGenerationService.generate_course_audios",
            new_callable=AsyncMock,
            return_value=[],
        ):
            response = await authorized_test_client.post(
                f"/courses/{test_course.slug}/generate-all-audios"
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["total_lessons_processed"] == 0
        assert len(data["generated_audios"]) == 0

    @pytest.mark.anyio
    async def test_get_lesson_audio_status_success(
        self, authorized_test_client: AsyncClient, test_course, session
    ):
        """Test getting audio generation status for a lesson."""
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
            status=LessonStatus.AUDIO_COMPLETED,
            script='[{"type": "speak", "content": "Hello"}]',
            audio_url="https://s3.amazonaws.com/audio/test.mp3",
            created_at=datetime.now(),
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        lesson_id = lesson.id

        response = await authorized_test_client.get(
            f"/courses/{test_course.slug}/lessons/{lesson_id}/audio-status"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["lesson_id"] == lesson_id
        assert data["status"] == LessonStatus.AUDIO_COMPLETED.value
        assert data["audio_url"] == "https://s3.amazonaws.com/audio/test.mp3"

    @pytest.mark.anyio
    async def test_get_lesson_audio_status_unauthorized(
        self, test_client: AsyncClient, test_course
    ):
        """Test unauthorized access is rejected."""
        response = await test_client.get(
            f"/courses/{test_course.slug}/lessons/1/audio-status"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.anyio
    async def test_get_lesson_audio_status_not_found(
        self, authorized_test_client: AsyncClient, test_course
    ):
        """Test error when lesson does not exist."""
        response = await authorized_test_client.get(
            f"/courses/{test_course.slug}/lessons/99999/audio-status"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_get_lesson_audio_status_no_audio(
        self, authorized_test_client: AsyncClient, test_course, session
    ):
        """Test status when lesson has no audio yet."""
        from senda.infrastructure.models import Course, Lesson

        course = await session.get(Course, test_course.id)
        lesson = Lesson(
            course_id=course.id,
            lesson_number=1,
            title="No Audio Lesson",
            core_practice="Breathing",
            key_point="Focus",
            tone="calm",
            duration_minutes=10,
            status=LessonStatus.SCRIPT_COMPLETED,
            script='[{"type": "speak", "content": "Hello"}]',
            audio_url=None,
            created_at=datetime.now(),
        )
        session.add(lesson)
        await session.commit()
        await session.refresh(lesson)
        lesson_id = lesson.id

        response = await authorized_test_client.get(
            f"/courses/{test_course.slug}/lessons/{lesson_id}/audio-status"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["lesson_id"] == lesson_id
        assert data["status"] == LessonStatus.SCRIPT_COMPLETED.value
        assert data["audio_url"] is None
