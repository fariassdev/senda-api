import contextlib
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from senda.core.config import get_app_settings
from senda.core.settings.base import BaseAppSettings
from senda.domain.mapper import IModelMapper
from senda.domain.repositories.course import ICourseRepository
from senda.domain.repositories.course_tag import ICourseTagRepository
from senda.domain.repositories.favorite import IFavoriteRepository
from senda.domain.repositories.follower import IFollowerRepository
from senda.domain.repositories.lesson import ILessonRepository
from senda.domain.repositories.tag import ITagRepository
from senda.domain.repositories.user import IUserRepository
from senda.domain.services.audio_generation import (
    IAudioGenerationService,
    IAudioProvider,
    IStorageProvider,
)
from senda.domain.services.auth import IUserAuthService
from senda.domain.services.auth_token import IAuthTokenService
from senda.domain.services.course import ICourseGenerationProvider, ICourseService
from senda.domain.services.lesson import ILessonService
from senda.domain.services.profile import IProfileService
from senda.domain.services.script_generation import (
    ILessonScriptProvider,
    IScriptGenerationService,
)
from senda.domain.services.tag import ITagService
from senda.domain.services.user import IUserService
from senda.infrastructure.config.gemini_config import GeminiConfig
from senda.infrastructure.loaders.prompt_loader import PromptLoader
from senda.infrastructure.mappers.course import CourseModelMapper
from senda.infrastructure.mappers.lesson import LessonModelMapper
from senda.infrastructure.mappers.tag import TagModelMapper
from senda.infrastructure.mappers.user import UserModelMapper
from senda.infrastructure.providers.gemini_course_generation_provider import (
    GeminiCourseGenerationProvider,
)
from senda.infrastructure.providers.gemini_script_generation_provider import (
    GeminiLessonScriptProvider,
)
from senda.infrastructure.providers.kokoro_audio_provider import KokoroAudioProvider
from senda.infrastructure.providers.s3_storage_provider import S3StorageProvider
from senda.infrastructure.repositories.course import CourseRepository
from senda.infrastructure.repositories.course_tag import CourseTagRepository
from senda.infrastructure.repositories.favorite import FavoriteRepository
from senda.infrastructure.repositories.follower import FollowerRepository
from senda.infrastructure.repositories.lesson import LessonRepository
from senda.infrastructure.repositories.tag import TagRepository
from senda.infrastructure.repositories.user import UserRepository
from senda.infrastructure.utils.audio_processor import AudioProcessor
from senda.services.audio_generation import AudioGenerationService
from senda.services.auth import UserAuthService
from senda.services.auth_token import AuthTokenService
from senda.services.course import CourseService
from senda.services.lesson import LessonService
from senda.services.profile import ProfileService
from senda.services.script_generation import ScriptGenerationService
from senda.services.tag import TagService
from senda.services.user import UserService


class Container:
    """Dependency injector project container."""

    def __init__(self, settings: BaseAppSettings) -> None:
        self._settings = settings
        self._engine = create_async_engine(**settings.sqlalchemy_engine_props)
        self._session = async_sessionmaker(bind=self._engine, expire_on_commit=False)

    @contextlib.asynccontextmanager
    async def context_session(self) -> AsyncIterator[AsyncSession]:
        session = self._session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self._session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @staticmethod
    def user_model_mapper() -> IModelMapper:
        return UserModelMapper()

    @staticmethod
    def tag_model_mapper() -> IModelMapper:
        return TagModelMapper()

    @staticmethod
    def course_model_mapper() -> IModelMapper:
        return CourseModelMapper()

    @staticmethod
    def lesson_model_mapper() -> IModelMapper:
        return LessonModelMapper()

    def user_repository(self) -> IUserRepository:
        return UserRepository(user_mapper=self.user_model_mapper())

    @staticmethod
    def follower_repository() -> IFollowerRepository:
        return FollowerRepository()

    def tags_repository(self) -> ITagRepository:
        return TagRepository(tag_mapper=self.tag_model_mapper())

    def course_repository(self) -> ICourseRepository:
        return CourseRepository(course_mapper=self.course_model_mapper())

    def course_tag_repository(self) -> ICourseTagRepository:
        return CourseTagRepository(tag_mapper=self.tag_model_mapper())

    def lesson_repository(self) -> ILessonRepository:
        return LessonRepository(lesson_mapper=self.lesson_model_mapper())

    @staticmethod
    def favorite_repository() -> IFavoriteRepository:
        return FavoriteRepository()

    def auth_token_service(self) -> IAuthTokenService:
        return AuthTokenService(
            secret_key=self._settings.jwt_secret_key,
            token_expiration_minutes=self._settings.jwt_token_expiration_minutes,
            algorithm=self._settings.jwt_algorithm,
        )

    def user_auth_service(self) -> IUserAuthService:
        return UserAuthService(
            user_service=self.user_service(),
            auth_token_service=self.auth_token_service(),
        )

    def user_service(self) -> IUserService:
        return UserService(user_repo=self.user_repository())

    def profile_service(self) -> IProfileService:
        return ProfileService(
            user_service=self.user_service(), follower_repo=self.follower_repository()
        )

    def tag_service(self) -> ITagService:
        return TagService(tag_repo=self.tags_repository())

    def prompt_loader(self) -> PromptLoader:
        """Creates PromptLoader for loading AI prompts from files."""
        return PromptLoader()

    def course_generation_provider(self) -> ICourseGenerationProvider | None:
        """
        Creates Gemini course generation provider if API key is configured.
        Returns None if Gemini is not configured.
        """
        if (
            not hasattr(self._settings, "gemini_api_key")
            or not self._settings.gemini_api_key
        ):
            return None

        config = GeminiConfig(api_key=self._settings.gemini_api_key)
        return GeminiCourseGenerationProvider(
            config=config, prompt_loader=self.prompt_loader()
        )

    def script_generation_provider(self) -> ILessonScriptProvider | None:
        """
        Creates Gemini script generation provider if API key is configured.
        Returns None if Gemini is not configured.
        """
        if (
            not hasattr(self._settings, "gemini_api_key")
            or not self._settings.gemini_api_key
        ):
            return None

        config = GeminiConfig(api_key=self._settings.gemini_api_key)
        return GeminiLessonScriptProvider(
            config=config, prompt_loader=self.prompt_loader()
        )

    def course_service(self) -> ICourseService:
        return CourseService(
            course_repo=self.course_repository(),
            course_tag_repo=self.course_tag_repository(),
            favorite_repo=self.favorite_repository(),
            profile_service=self.profile_service(),
            lesson_repo=self.lesson_repository(),
            generation_provider=self.course_generation_provider(),
        )

    def lesson_service(self) -> ILessonService:
        return LessonService(
            course_repo=self.course_repository(), lesson_repo=self.lesson_repository()
        )

    def script_generation_service(self) -> IScriptGenerationService:
        return ScriptGenerationService(
            course_repo=self.course_repository(),
            lesson_repo=self.lesson_repository(),
            script_provider=self.script_generation_provider(),
        )

    def audio_provider(self) -> IAudioProvider:
        """Creates Kokoro TTS audio provider."""
        api_url = getattr(
            self._settings, "kokoro_api_url", "http://localhost:8880/v1/audio/speech"
        )
        return KokoroAudioProvider(api_url=api_url)

    def storage_provider(self) -> IStorageProvider:
        """Creates S3 storage provider."""
        bucket_name = getattr(self._settings, "aws_s3_bucket", "senda-ai")
        region = getattr(self._settings, "aws_region", "us-east-1")
        return S3StorageProvider(bucket_name=bucket_name, region=region)

    @staticmethod
    def audio_processor() -> AudioProcessor:
        """Creates audio processor utility."""
        from senda.core.config import get_app_settings

        settings = get_app_settings()
        max_concurrent_tts = getattr(settings, "max_concurrent_tts", 3)
        return AudioProcessor(max_concurrent_tts=max_concurrent_tts)

    def audio_generation_service(self) -> IAudioGenerationService:
        """Creates audio generation service."""
        max_concurrent_lessons = getattr(self._settings, "max_concurrent_lessons", 5)
        return AudioGenerationService(
            course_repo=self.course_repository(),
            lesson_repo=self.lesson_repository(),
            audio_provider=self.audio_provider(),
            storage_provider=self.storage_provider(),
            audio_processor=self.audio_processor(),
            max_concurrent_lessons=max_concurrent_lessons,
        )


container = Container(settings=get_app_settings())
