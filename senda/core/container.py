import contextlib
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from senda.core.config import get_app_settings
from senda.core.settings.base import BaseAppSettings
from senda.core.wiring.audio import build_audio_generation_service, build_voice_service
from senda.core.wiring.gemini import (
    build_course_generation_provider,
    build_script_generation_provider,
)
from senda.domain.mapper import IModelMapper
from senda.domain.repositories.audio_generation_job import IAudioGenerationJobRepository
from senda.domain.repositories.course import ICourseRepository
from senda.domain.repositories.course_tag import ICourseTagRepository
from senda.domain.repositories.favorite import IFavoriteRepository
from senda.domain.repositories.follower import IFollowerRepository
from senda.domain.repositories.lesson import ILessonRepository
from senda.domain.repositories.lesson_audio import ILessonAudioRepository
from senda.domain.repositories.tag import ITagRepository
from senda.domain.repositories.user import IUserRepository
from senda.domain.repositories.voice import IVoiceRepository
from senda.domain.services.audio_generation import IAudioGenerationService
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
from senda.domain.services.voice import IVoiceService
from senda.infrastructure.loaders.prompt_loader import PromptLoader
from senda.infrastructure.mappers.audio_generation_job import (
    AudioGenerationJobModelMapper,
)
from senda.infrastructure.mappers.course import CourseModelMapper
from senda.infrastructure.mappers.lesson import LessonModelMapper
from senda.infrastructure.mappers.lesson_audio import LessonAudioModelMapper
from senda.infrastructure.mappers.tag import TagModelMapper
from senda.infrastructure.mappers.user import UserModelMapper
from senda.infrastructure.mappers.voice import VoiceModelMapper
from senda.infrastructure.repositories.audio_generation_job import (
    AudioGenerationJobRepository,
)
from senda.infrastructure.repositories.course import CourseRepository
from senda.infrastructure.repositories.course_tag import CourseTagRepository
from senda.infrastructure.repositories.favorite import FavoriteRepository
from senda.infrastructure.repositories.follower import FollowerRepository
from senda.infrastructure.repositories.lesson import LessonRepository
from senda.infrastructure.repositories.lesson_audio import LessonAudioRepository
from senda.infrastructure.repositories.tag import TagRepository
from senda.infrastructure.repositories.user import UserRepository
from senda.infrastructure.repositories.voice import VoiceRepository
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

    @staticmethod
    def lesson_audio_model_mapper() -> IModelMapper:
        return LessonAudioModelMapper()

    @staticmethod
    def audio_generation_job_model_mapper() -> IModelMapper:
        return AudioGenerationJobModelMapper()

    def voice_model_mapper(self) -> IModelMapper:
        base_url = f"https://{self._settings.aws_s3_bucket}.s3.amazonaws.com"
        return VoiceModelMapper(base_url=base_url)

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

    def lesson_audio_repository(self) -> ILessonAudioRepository:
        return LessonAudioRepository(
            lesson_audio_mapper=self.lesson_audio_model_mapper()
        )

    def audio_generation_job_repository(self) -> IAudioGenerationJobRepository:
        return AudioGenerationJobRepository(
            job_mapper=self.audio_generation_job_model_mapper()
        )

    def voice_repository(self) -> IVoiceRepository:
        return VoiceRepository(voice_mapper=self.voice_model_mapper())

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
        return PromptLoader()

    def course_generation_provider(self) -> ICourseGenerationProvider | None:
        return build_course_generation_provider(self._settings, self.prompt_loader())

    def script_generation_provider(self) -> ILessonScriptProvider | None:
        return build_script_generation_provider(self._settings, self.prompt_loader())

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
            course_repo=self.course_repository(),
            lesson_repo=self.lesson_repository(),
            lesson_audio_repo=self.lesson_audio_repository(),
        )

    def script_generation_service(self) -> IScriptGenerationService:
        return ScriptGenerationService(
            course_repo=self.course_repository(),
            lesson_repo=self.lesson_repository(),
            session_factory=self._session,
            script_provider=self.script_generation_provider(),
        )

    def audio_generation_service(self) -> IAudioGenerationService:
        return build_audio_generation_service(
            settings=self._settings,
            course_repo=self.course_repository(),
            lesson_repo=self.lesson_repository(),
            voice_repo=self.voice_repository(),
            job_repo=self.audio_generation_job_repository(),
            lesson_audio_repo=self.lesson_audio_repository(),
            session_factory=self._session,
        )

    def voice_service(self) -> IVoiceService:
        return build_voice_service(
            settings=self._settings,
            voice_repo=self.voice_repository(),
            lesson_audio_repo=self.lesson_audio_repository(),
        )


container = Container(settings=get_app_settings())
