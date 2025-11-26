"""
Test suite for course generation service logic.
Tests business logic without database or external API calls.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from senda.core.enums import DifficultyLevel
from senda.core.exceptions import CourseGenerationException
from senda.domain.dtos.course import CourseDTO
from senda.domain.dtos.course_generation import (
    CourseGenerationRequestDTO,
    CourseStructureDTO,
    LessonStructureDTO,
)
from senda.domain.dtos.lesson import LessonDTO
from senda.services.course import CourseService


class TestCourseServiceGeneration:
    """Test suite for CourseService.create_course_from_prompt"""

    @pytest.fixture
    def mock_course_repo(self):
        """Mock course repository"""
        return Mock()

    @pytest.fixture
    def mock_lesson_repo(self):
        """Mock lesson repository"""
        return Mock()

    @pytest.fixture
    def mock_course_tag_repo(self):
        """Mock course tag repository"""
        return Mock()

    @pytest.fixture
    def mock_favorite_repo(self):
        """Mock favorite repository"""
        return Mock()

    @pytest.fixture
    def mock_profile_service(self):
        """Mock profile service"""
        return Mock()

    @pytest.fixture
    def mock_generation_provider(self):
        """Mock AI generation provider"""
        return AsyncMock()

    @pytest.fixture
    def course_service(
        self,
        mock_course_repo,
        mock_lesson_repo,
        mock_course_tag_repo,
        mock_favorite_repo,
        mock_profile_service,
        mock_generation_provider,
    ):
        """Create CourseService with mocked dependencies"""
        return CourseService(
            course_repo=mock_course_repo,
            lesson_repo=mock_lesson_repo,
            course_tag_repo=mock_course_tag_repo,
            favorite_repo=mock_favorite_repo,
            profile_service=mock_profile_service,
            generation_provider=mock_generation_provider,
        )

    @pytest.fixture
    def mock_session(self):
        """Mock database session"""
        return Mock(spec=AsyncSession)

    @pytest.fixture
    def sample_generation_request(self):
        """Sample generation request"""
        return CourseGenerationRequestDTO(
            user_id=1,
            prompt="Create mindfulness course",
            difficulty_level=DifficultyLevel.BEGINNER,
        )

    @pytest.fixture
    def sample_course_structure(self):
        """Sample generated course structure"""
        return CourseStructureDTO(
            title="Mindfulness Basics",
            description="Learn mindfulness",
            duration_days=7,
            difficulty_level=DifficultyLevel.BEGINNER,
            tags=["mindfulness"],
            lessons=[
                LessonStructureDTO(
                    title="Day 1",
                    core_practice="Breathing",
                    key_point="Focus",
                    tone="calm",
                    duration_minutes=10,
                    order=1,
                )
            ],
        )

    # Test: Successful course and lessons creation
    @pytest.mark.asyncio
    async def test_create_course_from_prompt_success(
        self,
        course_service,
        mock_session,
        sample_generation_request,
        sample_course_structure,
        mock_generation_provider,
        mock_lesson_repo,
    ):
        """Test successful course generation with lessons"""
        # Setup mocks
        mock_generation_provider.generate_course_structure.return_value = (
            sample_course_structure
        )

        from datetime import datetime

        from senda.domain.dtos.course import CourseAuthorDTO

        created_course = CourseDTO(
            id=1,
            author_id=1,
            slug="mindfulness-basics",
            title="Mindfulness Basics",
            description="Learn mindfulness",
            difficulty_level="Beginner",
            active=False,
            image_placeholder_url=None,
            tags=["mindfulness"],
            author=CourseAuthorDTO(username="test"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            favorited=False,
            favorites_count=0,
        )

        created_lesson = LessonDTO(
            id=1,
            course_id=1,
            lesson_number=1,
            title="Day 1",
            core_practice="Breathing",
            key_point="Focus",
            tone="calm",
            duration_minutes=10,
            status="draft",
            script=None,
            audio_url=None,
            script_generated_at=None,
            audio_generated_at=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Mock service methods
        course_service.create_new_course = AsyncMock(return_value=created_course)
        mock_lesson_repo.add = AsyncMock(return_value=created_lesson)

        # Execute
        course, lessons = await course_service.create_course_from_prompt(
            session=mock_session, request=sample_generation_request
        )

        # Assert
        assert course.id == 1
        assert len(lessons) == 1
        assert lessons[0].lesson_number == 1
        mock_generation_provider.generate_course_structure.assert_called_once()

    # Test: No generation provider configured
    @pytest.mark.asyncio
    async def test_create_course_from_prompt_no_provider(
        self, mock_session, sample_generation_request
    ):
        """Test error when no generation provider is configured"""
        service = CourseService(
            course_repo=Mock(),
            lesson_repo=Mock(),
            course_tag_repo=Mock(),
            favorite_repo=Mock(),
            profile_service=Mock(),
            generation_provider=None,
        )

        with pytest.raises(CourseGenerationException) as exc_info:
            await service.create_course_from_prompt(
                session=mock_session, request=sample_generation_request
            )

        assert "not configured" in str(exc_info.value)

    # Test: Provider raises exception
    @pytest.mark.asyncio
    async def test_create_course_from_prompt_provider_fails(
        self,
        course_service,
        mock_session,
        sample_generation_request,
        mock_generation_provider,
    ):
        """Test handling when provider fails"""
        mock_generation_provider.generate_course_structure.side_effect = Exception(
            "API Error"
        )

        with pytest.raises(CourseGenerationException) as exc_info:
            await course_service.create_course_from_prompt(
                session=mock_session, request=sample_generation_request
            )

        assert "Failed to create course" in str(exc_info.value)

    # Test: Course creation fails
    @pytest.mark.asyncio
    async def test_create_course_from_prompt_course_creation_fails(
        self,
        course_service,
        mock_session,
        sample_generation_request,
        sample_course_structure,
        mock_generation_provider,
    ):
        """Test handling when course creation fails"""
        mock_generation_provider.generate_course_structure.return_value = (
            sample_course_structure
        )
        course_service.create_new_course = AsyncMock(side_effect=Exception("DB Error"))

        with pytest.raises(CourseGenerationException):
            await course_service.create_course_from_prompt(
                session=mock_session, request=sample_generation_request
            )
