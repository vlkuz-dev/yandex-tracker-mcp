from __future__ import annotations

import pytest

from yandex_tracker_mcp.config import Settings
from yandex_tracker_mcp.errors import TrackerConfigError


def test_settings_from_env_with_org_id() -> None:
    settings = Settings.from_env(
        {
            "YANDEX_TRACKER_TOKEN": "token",
            "YANDEX_TRACKER_ORG_ID": "12345",
        }
    )

    headers = settings.headers()
    assert headers["Authorization"] == "OAuth token"
    assert headers["X-Org-ID"] == "12345"
    assert "X-Cloud-Org-ID" not in headers


def test_settings_from_env_with_cloud_org() -> None:
    settings = Settings.from_env(
        {
            "YANDEX_TRACKER_TOKEN": "token",
            "YANDEX_TRACKER_TOKEN_TYPE": "Bearer",
            "YANDEX_TRACKER_CLOUD_ORG_ID": "aoid",
        }
    )

    headers = settings.headers()
    assert headers["Authorization"] == "Bearer token"
    assert headers["X-Cloud-Org-ID"] == "aoid"
    assert "X-Org-ID" not in headers


def test_settings_fail_when_no_org_header() -> None:
    with pytest.raises(TrackerConfigError):
        Settings.from_env(
            {
                "YANDEX_TRACKER_TOKEN": "token",
            }
        )


def test_settings_fail_when_both_org_headers_set() -> None:
    with pytest.raises(TrackerConfigError):
        Settings.from_env(
            {
                "YANDEX_TRACKER_TOKEN": "token",
                "YANDEX_TRACKER_ORG_ID": "1",
                "YANDEX_TRACKER_CLOUD_ORG_ID": "2",
            }
        )


def test_settings_fail_on_invalid_token_type() -> None:
    with pytest.raises(TrackerConfigError):
        Settings.from_env(
            {
                "YANDEX_TRACKER_TOKEN": "token",
                "YANDEX_TRACKER_ORG_ID": "1",
                "YANDEX_TRACKER_TOKEN_TYPE": "Basic",
            }
        )

