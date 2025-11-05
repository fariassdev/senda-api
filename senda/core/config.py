from functools import lru_cache

from senda.core.settings.app import AppSettings
from senda.core.settings.base import AppEnvTypes, BaseAppSettings
from senda.core.settings.development import DevAppSettings
from senda.core.settings.production import ProdAppSettings
from senda.core.settings.test import TestAppSettings

AppEnvType = DevAppSettings | TestAppSettings | ProdAppSettings

environments: dict[str, type[AppEnvType]] = {  # type: ignore
    AppEnvTypes.development: DevAppSettings,
    AppEnvTypes.testing: TestAppSettings,
    AppEnvTypes.production: ProdAppSettings,
}


@lru_cache
def get_app_settings() -> AppSettings:
    """
    Return application config.
    """
    app_env = BaseAppSettings().app_env
    config = environments[app_env]
    return config()  # type: ignore
