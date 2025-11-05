import logging

from pydantic import computed_field

from senda.core.settings.app import AppSettings


class DevAppSettings(AppSettings):
    """
    Development application settings.
    """

    debug: bool = True

    title: str = "[DEV] Senda API"

    logging_level: int = logging.DEBUG

    class Config(AppSettings.Config):
        env_file = ".env.dev"

    @computed_field  # type: ignore
    @property
    def sqlalchemy_engine_props(self) -> dict:
        return {"url": self.sql_db_uri, "echo": True}
