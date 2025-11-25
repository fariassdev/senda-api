import os
from collections.abc import Generator
from datetime import datetime
from typing import TypeAlias
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy_utils import create_database, database_exists, drop_database

from senda.app import create_app
from senda.core.config import get_app_settings
from senda.core.container import Container
from senda.core.dependencies import IAuthTokenService, ICourseService
from senda.core.enums import DifficultyLevel, UserRole
from senda.core.settings.base import BaseAppSettings
from senda.domain.dtos.course import CourseDTO, CreateCourseDTO
from senda.domain.dtos.course_generation import CourseStructureDTO, LessonStructureDTO
from senda.domain.dtos.user import CreateUserDTO, UserDTO
from senda.domain.repositories.course import ICourseRepository
from senda.domain.repositories.user import IUserRepository
from senda.infrastructure.models import Base

SetupFixture: TypeAlias = None


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(autouse=True)
def check_app_env_mode_enabled() -> None:
    assert os.getenv("APP_ENV") == "test"


@pytest.fixture(autouse=True)
def mock_gemini_api_globally():
    """
    Global mock for Gemini API _call_gemini_api method.
    This mocks all GeminiCourseGenerationProvider instances by default.

    By default returns an AsyncMock that does nothing.
    Tests should configure the mock's return_value or side_effect as needed.
    """
    from senda.infrastructure.providers.gemini_course_generation_provider import (
        GeminiCourseGenerationProvider,
    )

    mock_call = AsyncMock()

    with patch.object(GeminiCourseGenerationProvider, "_call_gemini_api", mock_call):
        yield mock_call


@pytest.fixture(scope="session")
def create_test_db(settings: BaseAppSettings) -> Generator[None, None, None]:
    test_db_sql_uri = settings.sql_db_uri.set(drivername="postgresql")

    if database_exists(url=test_db_sql_uri):
        drop_database(url=test_db_sql_uri)

    create_database(url=test_db_sql_uri)
    yield

    drop_database(url=test_db_sql_uri)


@pytest.fixture(autouse=True)
def create_tables(
    settings: BaseAppSettings, create_test_db: SetupFixture
) -> Generator[None, None, None]:
    engine = create_engine(
        url=settings.sql_db_uri.set(drivername="postgresql"),
        isolation_level="AUTOCOMMIT",
    )
    Base.metadata.create_all(bind=engine)
    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def application(create_test_db: SetupFixture) -> FastAPI:
    return create_app()


@pytest.fixture(scope="session")
def settings() -> BaseAppSettings:
    return get_app_settings()


@pytest.fixture(scope="session")
def di_container(settings: BaseAppSettings) -> Container:
    return Container(settings=settings)


@pytest.fixture
async def session(di_container: Container) -> AsyncSession:
    async with di_container.context_session() as session:
        yield session


@pytest.fixture
def user_repository(di_container: Container) -> IUserRepository:
    return di_container.user_repository()


@pytest.fixture
def course_repository(di_container: Container) -> ICourseRepository:
    return di_container.course_repository()


@pytest.fixture
def course_service(di_container: Container) -> ICourseService:
    return di_container.course_service()


@pytest.fixture
def auth_token_service(di_container: Container) -> IAuthTokenService:
    return di_container.auth_token_service()


@pytest.fixture
def user_to_create() -> CreateUserDTO:
    return CreateUserDTO(username="test", email="test@gmail.com", password="password")


@pytest.fixture
def course_to_create() -> CreateCourseDTO:
    return CreateCourseDTO(
        title="Test Course",
        description="Test Description",
        difficulty_level="Beginner",
        tags=["tag1", "tag2"],
    )


@pytest.fixture
def not_exists_user() -> UserDTO:
    dto = UserDTO(
        username="username",
        email="email",
        password_hash="hash",
        bio="bio",
        image_url="link",
        name="Test User",
        role=UserRole.USER,
        created_at=datetime.now(),
    )
    dto.id = 9999
    return dto


@pytest.fixture
async def test_user(
    session: AsyncSession,
    user_repository: IUserRepository,
    user_to_create: CreateUserDTO,
) -> UserDTO:
    return await user_repository.add(session=session, create_item=user_to_create)


@pytest.fixture
async def test_course(
    session: AsyncSession,
    course_service: ICourseService,
    course_to_create: CreateCourseDTO,
    test_user: UserDTO,
) -> CourseDTO:
    return await course_service.create_new_course(
        session=session, author_id=test_user.id, course_to_create=course_to_create
    )


@pytest.fixture
async def jwt_token(auth_token_service: IAuthTokenService, test_user: UserDTO) -> str:
    return auth_token_service.generate_jwt_token(user=test_user)


@pytest.fixture
async def not_exists_jwt_token(
    auth_token_service: IAuthTokenService, not_exists_user: UserDTO
) -> str:
    return auth_token_service.generate_jwt_token(user=not_exists_user)


@pytest.fixture
async def test_client(application: FastAPI) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver/api",
        headers={"Content-Type": "application/json"},
    ) as client:
        yield client


@pytest.fixture
async def authorized_test_client(application: FastAPI, jwt_token: str) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver/api",
        headers={
            "Authorization": f"Token {jwt_token}",
            "Content-Type": "application/json",
        },
    ) as client:
        yield client


@pytest.fixture
async def admin_user(
    session: AsyncSession, user_repository: IUserRepository
) -> UserDTO:
    """Create an admin user for testing."""
    admin_dto = CreateUserDTO(
        username="admin",
        email="admin@test.com",
        password="adminpass123",
        role=UserRole.ADMIN,
    )
    return await user_repository.add(session=session, create_item=admin_dto)


@pytest.fixture
async def admin_jwt_token(
    auth_token_service: IAuthTokenService, admin_user: UserDTO
) -> str:
    """Generate JWT token for admin user."""
    return auth_token_service.generate_jwt_token(user=admin_user)


@pytest.fixture
async def admin_client(application: FastAPI, admin_jwt_token: str) -> AsyncClient:
    """AsyncClient with admin authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://testserver/api",
        headers={
            "Authorization": f"Token {admin_jwt_token}",
            "Content-Type": "application/json",
        },
    ) as client:
        yield client
