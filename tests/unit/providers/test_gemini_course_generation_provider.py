"""
Test suite for GeminiCourseGenerationProvider.
Tests Gemini API integration without actual API calls.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from google.genai import errors

from senda.api.schemas.responses.gemini_schemas import (
    GeminiCourseSchema,
    GeminiLessonSchema,
)
from senda.core.enums import DifficultyLevel
from senda.core.exceptions import (
    AIProviderUnavailableException,
    CourseGenerationException,
    InvalidPromptException,
)
from senda.domain.dtos.course_generation import CourseGenerationRequestDTO
from senda.infrastructure.providers.gemini_course_generation_provider import (
    GeminiCourseGenerationProvider,
    gemini_schema_to_structure_dto,
)


class TestGeminiCourseGenerationProvider:
    """Test suite for GeminiCourseGenerationProvider"""

    @pytest.fixture
    def mock_config(self):
        """Mock Gemini configuration"""
        config = Mock()
        config.api_key = "test-api-key"
        config.model = "gemini-2.0-flash-thinking-exp-01-21"
        config.thinking_budget = 16384
        return config

    @pytest.fixture
    def mock_prompt_loader(self):
        """Mock prompt loader"""
        loader = Mock()
        loader.load_prompt.return_value = "System instruction text"
        return loader

    @pytest.fixture
    def provider(self, mock_config, mock_prompt_loader):
        """Create provider instance with mocks"""
        with patch(
            "senda.infrastructure.providers.gemini_course_generation_provider.genai.Client"
        ):
            return GeminiCourseGenerationProvider(mock_config, mock_prompt_loader)

    @pytest.fixture
    def sample_request(self):
        """Sample generation request"""
        return CourseGenerationRequestDTO(
            user_id=1,
            prompt="Create a mindfulness course for beginners",
            difficulty_level=DifficultyLevel.BEGINNER,
        )

    @pytest.fixture
    def sample_gemini_response(self):
        """Sample Gemini API response"""
        return GeminiCourseSchema(
            title="Mindfulness for Beginners",
            description="Learn mindfulness basics",
            duration_days=7,
            difficulty_level=DifficultyLevel.BEGINNER,
            tags=["mindfulness", "meditation"],
            lessons=[
                GeminiLessonSchema(
                    title="Introduction to Mindfulness",
                    core_practice="Breathing awareness",
                    key_point="Focus on breath",
                    tone="calm",
                    duration_minutes=10,
                    order=1,
                )
            ],
        )

    # Test: Successful generation
    @pytest.mark.asyncio
    async def test_generate_course_structure_success(
        self, provider, sample_request, sample_gemini_response
    ):
        """Test successful course generation"""
        provider._call_gemini_api = AsyncMock(return_value=sample_gemini_response)

        result = await provider.generate_course_structure(sample_request)

        assert result.title == "Mindfulness for Beginners"
        assert len(result.lessons) == 1
        assert result.difficulty_level == DifficultyLevel.BEGINNER

    # Test: Invalid prompt (400 error)
    @pytest.mark.asyncio
    async def test_generate_course_structure_invalid_prompt(
        self, provider, sample_request
    ):
        """Test invalid prompt handling"""
        api_error = errors.APIError(
            code=400, response_json={"error": {"message": "Invalid prompt"}}
        )
        provider._call_gemini_api = AsyncMock(side_effect=api_error)

        with pytest.raises(InvalidPromptException) as exc_info:
            await provider.generate_course_structure(sample_request)

        assert "Invalid prompt" in str(exc_info.value)

    # Test: Rate limit (429 error)
    @pytest.mark.asyncio
    async def test_generate_course_structure_rate_limit(self, provider, sample_request):
        """Test rate limit handling"""
        api_error = errors.APIError(
            code=429, response_json={"error": {"message": "Rate limit exceeded"}}
        )
        provider._call_gemini_api = AsyncMock(side_effect=api_error)

        with pytest.raises(AIProviderUnavailableException) as exc_info:
            await provider.generate_course_structure(sample_request)

        assert "Rate limit" in str(exc_info.value)

    # Test: Service unavailable (503 error)
    @pytest.mark.asyncio
    async def test_generate_course_structure_service_unavailable(
        self, provider, sample_request
    ):
        """Test service unavailable handling"""
        api_error = errors.APIError(
            code=503, response_json={"error": {"message": "Service unavailable"}}
        )
        provider._call_gemini_api = AsyncMock(side_effect=api_error)

        with pytest.raises(AIProviderUnavailableException):
            await provider.generate_course_structure(sample_request)

    # Test: Timeout (408 error)
    @pytest.mark.asyncio
    async def test_generate_course_structure_timeout(self, provider, sample_request):
        """Test timeout handling"""
        api_error = errors.APIError(
            code=408, response_json={"error": {"message": "Request timeout"}}
        )
        provider._call_gemini_api = AsyncMock(side_effect=api_error)

        with pytest.raises(CourseGenerationException) as exc_info:
            await provider.generate_course_structure(sample_request)

        assert "timed out" in str(exc_info.value)

    # Test: Generic API error
    @pytest.mark.asyncio
    async def test_generate_course_structure_generic_api_error(
        self, provider, sample_request
    ):
        """Test generic API error handling"""
        api_error = errors.APIError(
            code=500, response_json={"error": {"message": "Internal error"}}
        )
        provider._call_gemini_api = AsyncMock(side_effect=api_error)

        with pytest.raises(CourseGenerationException):
            await provider.generate_course_structure(sample_request)

    # Test: Unexpected exception
    @pytest.mark.asyncio
    async def test_generate_course_structure_unexpected_error(
        self, provider, sample_request
    ):
        """Test unexpected error handling"""
        provider._call_gemini_api = AsyncMock(side_effect=ValueError("Unexpected"))

        with pytest.raises(CourseGenerationException) as exc_info:
            await provider.generate_course_structure(sample_request)

        # The error message includes "Course generation failed:" prefix
        assert "Course generation failed:" in str(exc_info.value)

    # Test: Enhanced prompt building
    def test_build_enhanced_prompt_with_difficulty(self, provider, sample_request):
        """Test prompt enhancement with difficulty level"""
        result = provider._build_enhanced_prompt(sample_request)

        assert sample_request.prompt in result
        # The difficulty level is stored as BEGINNER (uppercase enum value)
        assert "Difficulty level: BEGINNER" in result

    def test_build_enhanced_prompt_without_difficulty(self, provider):
        """Test prompt enhancement without difficulty level"""
        request = CourseGenerationRequestDTO(
            user_id=1, prompt="Create a course", difficulty_level=None
        )

        result = provider._build_enhanced_prompt(request)

        assert result == "Create a course"

    # Test: Schema to DTO mapping
    def test_gemini_schema_to_structure_dto(self, sample_gemini_response):
        """Test mapping from Gemini schema to domain DTO"""
        result = gemini_schema_to_structure_dto(sample_gemini_response)

        assert result.title == sample_gemini_response.title
        assert result.description == sample_gemini_response.description
        assert len(result.lessons) == len(sample_gemini_response.lessons)
        assert result.lessons[0].title == sample_gemini_response.lessons[0].title

    # Test: System instruction loading
    def test_load_system_instruction(self, provider, mock_prompt_loader):
        """Test system instruction is loaded correctly"""
        mock_prompt_loader.load_prompt.assert_called_once_with(
            GeminiCourseGenerationProvider.SYSTEM_PROMPT_PATH
        )
