"""Unit tests run without database setup."""

from collections.abc import Generator

import pytest

from senda.core.settings.app import AppSettings


@pytest.fixture(scope="session")
def create_test_db() -> Generator[None, None, None]:
    yield


@pytest.fixture(autouse=True)
def create_tables(create_test_db: None) -> Generator[None, None, None]:
    yield


def make_app_settings(**overrides) -> AppSettings:
    defaults = {
        "secret_key": "test-secret-key",
        "postgres_host": "localhost",
        "postgres_port": 5432,
        "postgres_user": "test",
        "postgres_password": "test",
        "postgres_db": "test_db",
        "jwt_secret_key": "test-jwt-secret",
    }
    defaults.update(overrides)
    return AppSettings.model_construct(**defaults)
