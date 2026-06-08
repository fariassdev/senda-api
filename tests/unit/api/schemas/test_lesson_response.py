"""Tests for lesson response schema conversion."""

import datetime

import pytest

from senda.api.schemas.responses.lesson import LessonResponse
from senda.core.enums import LessonStatus, ScriptPartType
from senda.domain.dtos.lesson import LessonDTO
from senda.domain.dtos.script_generation import ScriptPartDTO


class TestLessonResponse:
    """Test lesson response schema."""

    def test_from_dto_with_script(self) -> None:
        """Test conversion from DTO to response with script."""
        # Arrange
        script_parts = [
            ScriptPartDTO(type=ScriptPartType.SPEAK, content="Welcome to the course."),
            ScriptPartDTO(type=ScriptPartType.PAUSE, duration=2.0),
        ]
        lesson_dto = LessonDTO(
            id=1,
            course_id=1,
            lesson_number=1,
            title="Introduction",
            core_practice="Breathing",
            key_point="Focus on breath",
            tone="Calm",
            duration_minutes=10,
            status=LessonStatus.SCRIPT_COMPLETED,
            script=script_parts,
            playlist_url=None,
            script_generated_at=datetime.datetime(2025, 11, 27, 12, 0, 0),
            audio_generated_at=None,
            created_at=datetime.datetime(2025, 11, 27, 10, 0, 0),
            updated_at=datetime.datetime(2025, 11, 27, 11, 0, 0),
        )

        # Act
        response = LessonResponse.from_dto(dto=lesson_dto)

        # Assert
        assert response.lesson.id == 1
        assert response.lesson.title == "Introduction"
        assert response.lesson.script is not None
        assert len(response.lesson.script) == 2
        assert response.lesson.script[0].type == ScriptPartType.SPEAK
        assert response.lesson.script[0].content == "Welcome to the course."
        assert response.lesson.script[1].type == ScriptPartType.PAUSE
        assert response.lesson.script[1].duration == 2.0

    def test_from_dto_with_hls_playlist(self) -> None:
        """Test conversion exposes HLS playlist from lesson_audio."""
        lesson_dto = LessonDTO(
            id=4,
            course_id=1,
            lesson_number=4,
            title="Day 4",
            core_practice="Meditation",
            key_point="Stillness",
            tone="Peaceful",
            duration_minutes=20,
            status=LessonStatus.AUDIO_COMPLETED,
            script=None,
            playlist_url="https://cdn.test/meditations/4/playlist.m3u8",
            script_generated_at=None,
            audio_generated_at=datetime.datetime(2025, 11, 27, 13, 0, 0),
            created_at=datetime.datetime(2025, 11, 27, 10, 0, 0),
            updated_at=datetime.datetime(2025, 11, 27, 13, 0, 0),
        )

        response = LessonResponse.from_dto(dto=lesson_dto)

        assert response.lesson.playlist_url == (
            "https://cdn.test/meditations/4/playlist.m3u8"
        )
        assert response.lesson.audio_generated_at == datetime.datetime(
            2025, 11, 27, 13, 0, 0
        )

    def test_from_dto_without_script(self) -> None:
        """Test conversion from DTO to response without script."""
        # Arrange
        lesson_dto = LessonDTO(
            id=2,
            course_id=1,
            lesson_number=2,
            title="Day 2",
            core_practice="Body scan",
            key_point="Awareness",
            tone="Gentle",
            duration_minutes=15,
            status=LessonStatus.PENDING,
            script=None,
            playlist_url=None,
            script_generated_at=None,
            audio_generated_at=None,
            created_at=datetime.datetime(2025, 11, 27, 10, 0, 0),
            updated_at=datetime.datetime(2025, 11, 27, 11, 0, 0),
        )

        # Act
        response = LessonResponse.from_dto(dto=lesson_dto)

        # Assert
        assert response.lesson.id == 2
        assert response.lesson.title == "Day 2"
        assert response.lesson.script is None

    def test_from_dto_with_empty_script(self) -> None:
        """Test conversion from DTO to response with empty script list."""
        # Arrange
        lesson_dto = LessonDTO(
            id=3,
            course_id=1,
            lesson_number=3,
            title="Day 3",
            core_practice="Meditation",
            key_point="Stillness",
            tone="Peaceful",
            duration_minutes=20,
            status=LessonStatus.PENDING,
            script=[],
            playlist_url=None,
            script_generated_at=None,
            audio_generated_at=None,
            created_at=datetime.datetime(2025, 11, 27, 10, 0, 0),
            updated_at=datetime.datetime(2025, 11, 27, 11, 0, 0),
        )

        # Act
        response = LessonResponse.from_dto(dto=lesson_dto)

        # Assert
        assert response.lesson.id == 3
        # Empty script list is treated as None due to falsy check
        assert response.lesson.script is None
