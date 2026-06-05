import logging
from typing import Any

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

    # CORS configuration - comma-separated string: "http://localhost:3000,https://example.com"
    cors_allowed_origins: str | None = None
    cors_allowed_origins_regex: str | None = None

    logging_level: int = logging.INFO

    class Config:
        validate_assignment = True

    @property
    def cors_origins_list(self) -> list[str] | None:
        """Parse cors_allowed_origins into a list."""
        if not self.cors_allowed_origins:
            return None
        origins = [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]
        return origins or None

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
