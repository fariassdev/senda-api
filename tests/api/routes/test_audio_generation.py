"""Integration tests for audio generation API endpoints."""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from senda.core.enums import LessonStatus
from senda.domain.dtos.audio_generation import (
    AudioGenerationResultDTO,
    BatchAudioGenerationResultDTO,
)
from senda.domain.dtos.script_generation import (
    BatchScriptGenerationResultDTO,
    ScriptGenerationResultDTO,
    ScriptPartDTO,
)


class TestAudioGenerationAPI:
    """Test suite for audio generation endpoints."""

    @pytest.mark.anyio
    async def test_generate_lesson_audio_success(
        self, admin_test_client: AsyncClient, test_user, test_course, session
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
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/lessons/{lesson_id}/generate-audio",
                json={"audio_config": {"voice_id": str(uuid4())}},
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
            f"/courses/{test_course.slug}/lessons/1/generate-audio",
            json={"audio_config": {"voice_id": str(uuid4())}},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.anyio
    async def test_generate_lesson_audio_user_not_admin(
        self, authorized_test_client: AsyncClient, test_course
    ):
        """Test unauthorized access is rejected."""
        response = await authorized_test_client.post(
            f"/courses/{test_course.slug}/lessons/1/generate-audio",
            json={"audio_config": {"voice_id": str(uuid4())}},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.anyio
    async def test_generate_lesson_audio_lesson_not_found(
        self, admin_test_client: AsyncClient, test_course
    ):
        """Test error when lesson does not exist."""
        from senda.core.exceptions import LessonNotFoundException

        with patch(
            "senda.services.audio_generation.AudioGenerationService.generate_lesson_audio",
            new_callable=AsyncMock,
            side_effect=LessonNotFoundException(),
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/lessons/99999/generate-audio",
                json={"audio_config": {"voice_id": str(uuid4())}},
            )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.anyio
    async def test_generate_lesson_audio_invalid_state(
        self, admin_test_client: AsyncClient, test_course, session
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
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/lessons/{lesson_id}/generate-audio",
                json={"audio_config": {"voice_id": str(uuid4())}},
            )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.anyio
    async def test_generate_course_audios_success(
        self, admin_test_client: AsyncClient, test_user, test_course, session
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

        mock_batch_result = BatchAudioGenerationResultDTO(
            results=mock_results, errors=[], total_requested=2
        )

        with patch(
            "senda.services.audio_generation.AudioGenerationService.generate_course_audios",
            new_callable=AsyncMock,
            return_value=mock_batch_result,
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/generate-batch-audios",
                json={"audio_config": {"voice_id": str(uuid4())}},
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
            f"/courses/{test_course.slug}/generate-batch-audios",
            json={"audio_config": {"voice_id": str(uuid4())}},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.anyio
    async def test_generate_course_audios_no_ready_lessons(
        self, admin_test_client: AsyncClient, test_course
    ):
        """Test bulk generation when no lessons are ready."""
        mock_batch_result = BatchAudioGenerationResultDTO(
            results=[], errors=[], total_requested=0
        )
        with patch(
            "senda.services.audio_generation.AudioGenerationService.generate_course_audios",
            new_callable=AsyncMock,
            return_value=mock_batch_result,
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/generate-batch-audios",
                json={"audio_config": {"voice_id": str(uuid4())}},
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


class TestBatchAudioGeneration:
    """Test suite for batch audio generation with lesson_ids filtering."""

    @pytest.mark.anyio
    async def test_generate_batch_audios_specific_lessons(
        self, admin_test_client: AsyncClient, test_course
    ):
        """Test generating audio for specific lesson IDs."""
        lesson_ids = [1, 2, 3]
        mock_results = [
            AudioGenerationResultDTO(
                lesson_id=1,
                audio_url="https://s3.amazonaws.com/audio/lesson1.mp3",
                generation_time_seconds=5.0,
                file_size_bytes=1024,
            ),
            AudioGenerationResultDTO(
                lesson_id=2,
                audio_url="https://s3.amazonaws.com/audio/lesson2.mp3",
                generation_time_seconds=6.0,
                file_size_bytes=2048,
            ),
        ]

        mock_batch_result = BatchAudioGenerationResultDTO(
            results=mock_results, errors=[], total_requested=2
        )

        with patch(
            "senda.services.audio_generation.AudioGenerationService.generate_course_audios",
            new_callable=AsyncMock,
            return_value=mock_batch_result,
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/generate-batch-audios",
                json={
                    "lesson_ids": lesson_ids,
                    "audio_config": {"voice_id": str(uuid4())},
                },
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_lessons_processed"] == 2
        assert len(data["generated_audios"]) == 2
        assert len(data["errors"]) == 0

    @pytest.mark.anyio
    async def test_generate_batch_audios_empty_array_generates_nothing(
        self, admin_test_client: AsyncClient, test_course
    ):
        """Test that empty lesson_ids array generates nothing."""
        mock_batch_result = BatchAudioGenerationResultDTO(
            results=[], errors=[], total_requested=0
        )
        with patch(
            "senda.services.audio_generation.AudioGenerationService.generate_course_audios",
            new_callable=AsyncMock,
            return_value=mock_batch_result,
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/generate-batch-audios",
                json={"lesson_ids": [], "audio_config": {"voice_id": str(uuid4())}},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_lessons_processed"] == 0
        assert len(data["generated_audios"]) == 0
        assert len(data["errors"]) == 0

    @pytest.mark.anyio
    async def test_generate_batch_audios_no_lesson_ids_generates_all(
        self, admin_test_client: AsyncClient, test_course
    ):
        """Test that omitting lesson_ids generates for all eligible lessons."""
        mock_results = [
            AudioGenerationResultDTO(
                lesson_id=1,
                audio_url="https://s3.amazonaws.com/audio/lesson1.mp3",
                generation_time_seconds=5.0,
                file_size_bytes=1024,
            ),
            AudioGenerationResultDTO(
                lesson_id=2,
                audio_url="https://s3.amazonaws.com/audio/lesson2.mp3",
                generation_time_seconds=6.0,
                file_size_bytes=2048,
            ),
        ]

        mock_batch_result = BatchAudioGenerationResultDTO(
            results=mock_results, errors=[], total_requested=2
        )

        with patch(
            "senda.services.audio_generation.AudioGenerationService.generate_course_audios",
            new_callable=AsyncMock,
            return_value=mock_batch_result,
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/generate-batch-audios",
                json={"audio_config": {"voice_id": str(uuid4())}},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_lessons_processed"] == 2
        assert len(data["errors"]) == 0


class TestBatchScriptGeneration:
    """Test suite for batch script generation with lesson_ids filtering."""

    @pytest.mark.anyio
    async def test_generate_batch_scripts_specific_lessons(
        self, admin_test_client: AsyncClient, test_course
    ):
        """Test generating scripts for specific lesson IDs."""
        from senda.core.enums import ScriptPartType

        lesson_ids = [1, 2]
        mock_results = [
            ScriptGenerationResultDTO(
                lesson_id=1,
                script=[
                    ScriptPartDTO(type=ScriptPartType.SPEAK, content="Test script 1")
                ],
                generation_time_seconds=3.0,
            ),
            ScriptGenerationResultDTO(
                lesson_id=2,
                script=[
                    ScriptPartDTO(type=ScriptPartType.SPEAK, content="Test script 2")
                ],
                generation_time_seconds=3.5,
            ),
        ]

        mock_batch_result = BatchScriptGenerationResultDTO(
            results=mock_results, errors=[], total_requested=2
        )

        with patch(
            "senda.services.script_generation.ScriptGenerationService.generate_course_scripts",
            new_callable=AsyncMock,
            return_value=mock_batch_result,
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/generate-batch-scripts",
                json={"lesson_ids": lesson_ids},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_lessons_processed"] == 2
        assert len(data["generated_scripts"]) == 2
        assert len(data["errors"]) == 0

    @pytest.mark.anyio
    async def test_generate_batch_scripts_empty_array_generates_nothing(
        self, admin_test_client: AsyncClient, test_course
    ):
        """Test that empty lesson_ids array generates nothing."""
        mock_batch_result = BatchScriptGenerationResultDTO(
            results=[], errors=[], total_requested=0
        )
        with patch(
            "senda.services.script_generation.ScriptGenerationService.generate_course_scripts",
            new_callable=AsyncMock,
            return_value=mock_batch_result,
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/generate-batch-scripts",
                json={"lesson_ids": []},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_lessons_processed"] == 0
        assert len(data["generated_scripts"]) == 0
        assert len(data["errors"]) == 0

    @pytest.mark.anyio
    async def test_generate_batch_scripts_no_lesson_ids_generates_all(
        self, admin_test_client: AsyncClient, test_course
    ):
        """Test that omitting lesson_ids generates for all eligible lessons."""
        from senda.core.enums import ScriptPartType

        mock_results = [
            ScriptGenerationResultDTO(
                lesson_id=1,
                script=[
                    ScriptPartDTO(type=ScriptPartType.SPEAK, content="Test script 1")
                ],
                generation_time_seconds=3.0,
            )
        ]

        mock_batch_result = BatchScriptGenerationResultDTO(
            results=mock_results, errors=[], total_requested=1
        )

        with patch(
            "senda.services.script_generation.ScriptGenerationService.generate_course_scripts",
            new_callable=AsyncMock,
            return_value=mock_batch_result,
        ):
            response = await admin_test_client.post(
                f"/courses/{test_course.slug}/generate-batch-scripts", json={}
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_lessons_processed"] == 1
        assert len(data["errors"]) == 0
