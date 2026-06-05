"""Factory functions for Gemini-backed generation providers."""

from senda.core.settings.base import BaseAppSettings
from senda.domain.services.course import ICourseGenerationProvider
from senda.domain.services.script_generation import ILessonScriptProvider
from senda.infrastructure.config.gemini_config import GeminiConfig
from senda.infrastructure.loaders.prompt_loader import PromptLoader
from senda.infrastructure.providers.gemini_course_generation_provider import (
    GeminiCourseGenerationProvider,
)
from senda.infrastructure.providers.gemini_script_generation_provider import (
    GeminiLessonScriptProvider,
)


def build_course_generation_provider(
    settings: BaseAppSettings, prompt_loader: PromptLoader
) -> ICourseGenerationProvider | None:
    if not settings.gemini_api_key:
        return None

    config = GeminiConfig(api_key=settings.gemini_api_key)
    return GeminiCourseGenerationProvider(config=config, prompt_loader=prompt_loader)


def build_script_generation_provider(
    settings: BaseAppSettings, prompt_loader: PromptLoader
) -> ILessonScriptProvider | None:
    if not settings.gemini_api_key:
        return None

    config = GeminiConfig(api_key=settings.gemini_api_key)
    return GeminiLessonScriptProvider(config=config, prompt_loader=prompt_loader)
