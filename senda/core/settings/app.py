import logging
from typing import Any

from pydantic import field_validator

from senda.core.settings.base import BaseAppSettings
from version import response


class AppSettings(BaseAppSettings):
    """
    Base application settings
    """

    debug: bool = False
    docs_url: str | None = "/"
    openapi_prefix: str = ""
    openapi_url: str | None = "/openapi.json"
    redoc_url: str | None = "/redoc"
    title: str = response["message"]
    version: str = response["version"]

    secret_key: str

    api_prefix: str = "/api/v1"

    # CORS configuration - can be set via CORS_ALLOWED_ORIGINS env var
    # as comma-separated string: "http://localhost:3000,https://example.com"
    cors_allowed_origins: list[str] = ["*"]

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated origins string into list."""
        if isinstance(v, str):
            # Handle comma-separated string from environment variable
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    logging_level: int = logging.INFO

    class Config:
        validate_assignment = True

    @property
    def fastapi_kwargs(self) -> dict[str, Any]:
        return {
            "debug": self.debug,
            "docs_url": self.docs_url,
            "openapi_prefix": self.openapi_prefix,
            "openapi_url": self.openapi_url,
            "redoc_url": self.redoc_url,
            "title": self.title,
            "version": self.version,
        }
