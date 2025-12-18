from senda.core.settings.app import AppSettings


class ProdAppSettings(AppSettings):
    """
    Production application settings.
    Disables API documentation for security.
    """

    # Disable docs in production for security
    docs_url: str | None = None
    redoc_url: str | None = None
    openapi_url: str | None = None

    class Config(AppSettings.Config):
        env_file = ".env"
