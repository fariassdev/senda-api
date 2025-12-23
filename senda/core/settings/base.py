from pydantic import computed_field
from pydantic_settings import BaseSettings
from sqlalchemy import URL


class AppEnvTypes:
    """
    Available application environments.
    """

    production = "prod"
    development = "dev"
    testing = "test"


class BaseAppSettings(BaseSettings):
    """
    Base application setting class.
    """

    app_env: str = AppEnvTypes.production

    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str

    jwt_secret_key: str
    jwt_token_expiration_minutes: int = 60 * 24 * 7  # one week.
    jwt_algorithm: str = "HS256"

    # AI Generation
    gemini_api_key: str | None = None

    # Audio Generation
    kokoro_api_url: str = "http://localhost:8880/v1/audio/speech"
    kokoro_api_timeout: float = (
        600.0  # Timeout in seconds (increased for Oracle Cloud cold starts)
    )
    aws_s3_bucket: str = "senda-ai"
    aws_region: str = "eu-west-1"

    # Audio Generation Concurrency
    max_concurrent_lessons: int = 5  # Max parallel lesson audio generations
    max_concurrent_tts: int = 3  # Max parallel TTS requests per lesson

    class Config:
        env_file = ".env"
        extra = "ignore"

    @computed_field  # type: ignore
    @property
    def sql_db_uri(self) -> URL:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.postgres_user,
            password=self.postgres_password,
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @computed_field  # type: ignore
    @property
    def sqlalchemy_engine_props(self) -> dict:
        return {"url": self.sql_db_uri}
