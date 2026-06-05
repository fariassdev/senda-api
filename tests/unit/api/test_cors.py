from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from senda.app import create_app
from tests.unit.conftest import make_app_settings

PREVIEW_ORIGIN = "https://my-project-git-feat-abc123-myteam.vercel.app"
PREVIEW_ORIGIN_REGEX = r"^https://my-project-[a-z0-9-]+-myteam\.vercel\.app$"
CORS_PREFLIGHT_PATH = "/api/health-check"


@pytest.fixture
def cors_client():
    def _create_client(**settings_overrides) -> TestClient:
        settings = make_app_settings(**settings_overrides)
        with patch("senda.app.get_app_settings", return_value=settings):
            return TestClient(create_app())

    return _create_client


def _preflight(client: TestClient, origin: str):
    return client.options(
        CORS_PREFLIGHT_PATH,
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )


def test_create_app_allows_multiple_static_origins(cors_client):
    client = cors_client(
        cors_allowed_origins="http://localhost:3000,https://my-project.vercel.app"
    )

    for origin in ("http://localhost:3000", "https://my-project.vercel.app"):
        response = _preflight(client, origin)
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin


def test_create_app_allows_literal_and_regex_origins(cors_client):
    client = cors_client(
        cors_allowed_origins="http://localhost:3000",
        cors_allowed_origins_regex=PREVIEW_ORIGIN_REGEX,
    )

    literal_response = _preflight(client, "http://localhost:3000")
    assert literal_response.status_code == 200
    assert (
        literal_response.headers.get("access-control-allow-origin")
        == "http://localhost:3000"
    )

    regex_response = _preflight(client, PREVIEW_ORIGIN)
    assert regex_response.status_code == 200
    assert regex_response.headers.get("access-control-allow-origin") == PREVIEW_ORIGIN

    blocked_response = _preflight(client, "https://malicious.example")
    assert blocked_response.status_code == 400
    assert "access-control-allow-origin" not in blocked_response.headers


@pytest.mark.parametrize(
    "settings_overrides",
    [
        {"cors_allowed_origins": None, "cors_allowed_origins_regex": None},
        {"cors_allowed_origins": "", "cors_allowed_origins_regex": ""},
    ],
    ids=["unset", "empty"],
)
def test_create_app_blocks_preflight_when_cors_unconfigured(
    cors_client, settings_overrides
):
    client = cors_client(**settings_overrides)

    response = _preflight(client, "http://localhost:3000")
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
