from senda.core.settings.app import AppSettings
from tests.unit.conftest import make_app_settings

PREVIEW_ORIGIN_REGEX = r"^https://my-project-[a-z0-9-]+-myteam\.vercel\.app$"


def test_app_settings_default_cors_origins():
    settings = make_app_settings()
    assert settings.cors_allowed_origins is None
    assert settings.cors_allowed_origins_regex is None
    assert settings.cors_origins_list is None
    assert AppSettings.model_fields["cors_allowed_origins"].default is None
    assert AppSettings.model_fields["cors_allowed_origins_regex"].default is None


def test_cors_origins_list_parses_literal_origins():
    settings = make_app_settings(
        cors_allowed_origins="http://localhost:3000,https://my-project.vercel.app"
    )
    assert settings.cors_origins_list == [
        "http://localhost:3000",
        "https://my-project.vercel.app",
    ]
    assert settings.cors_allowed_origins_regex is None


def test_cors_origins_list_strips_whitespace_and_ignores_empty_entries():
    settings = make_app_settings(
        cors_allowed_origins=" http://localhost:3000 , , https://my-project.vercel.app "
    )
    assert settings.cors_origins_list == [
        "http://localhost:3000",
        "https://my-project.vercel.app",
    ]


def test_cors_origins_list_returns_none_for_empty_string():
    settings = make_app_settings(cors_allowed_origins="")
    assert settings.cors_origins_list is None


def test_cors_origins_list_returns_none_for_whitespace_only():
    settings = make_app_settings(cors_allowed_origins="  ,  ")
    assert settings.cors_origins_list is None


def test_cors_allowed_origins_regex_without_literal_origins():
    settings = make_app_settings(
        cors_allowed_origins="", cors_allowed_origins_regex=PREVIEW_ORIGIN_REGEX
    )
    assert settings.cors_origins_list is None
    assert settings.cors_allowed_origins_regex == PREVIEW_ORIGIN_REGEX
