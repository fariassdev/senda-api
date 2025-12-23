import logging
from typing import Annotated, Any

from pydantic import BeforeValidator

from senda.core.settings.base import BaseAppSettings
from version import response


def parse_cors_origins(v: str | list[str] | None) -> list[str]:
    """Parse comma-separated origins string into list.

    Handles:
    - None or empty string: returns default ["*"]
    - Comma-separated string: splits and trims
    - Already a list: returns as-is
    """
    if v is None or v == "":
        return ["*"]
    if isinstance(v, str):
        origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        return origins if origins else ["*"]
    return v


# Type alias for CORS origins that handles string parsing before validation
CorsOrigins = Annotated[list[str], BeforeValidator(parse_cors_origins)]


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
    # Empty or missing value defaults to ["*"]
    cors_allowed_origins: CorsOrigins = ["*"]

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
