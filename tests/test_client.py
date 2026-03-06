from __future__ import annotations

import httpx
import pytest
import respx

from yandex_tracker_mcp.client import TrackerClient
from yandex_tracker_mcp.config import Settings
from yandex_tracker_mcp.errors import TrackerAPIError, TrackerConfigError
from yandex_tracker_mcp.models import OperationSpec


@pytest.fixture
def settings() -> Settings:
    return Settings.from_env(
        {
            "YANDEX_TRACKER_TOKEN": "token",
            "YANDEX_TRACKER_ORG_ID": "123",
            "YANDEX_TRACKER_BASE_URL": "https://api.tracker.yandex.net",
            "YANDEX_TRACKER_RETRIES": "1",
            "YANDEX_TRACKER_TIMEOUT_SECONDS": "5",
        }
    )


@respx.mock
@pytest.mark.asyncio
async def test_request_success_json(settings: Settings) -> None:
    route = respx.get("https://api.tracker.yandex.net/v3/myself").mock(
        return_value=httpx.Response(200, json={"uid": "1"})
    )

    client = TrackerClient(settings)
    payload = await client.request(method="GET", path="/v3/myself")

    assert route.called
    assert payload == {"uid": "1"}


@respx.mock
@pytest.mark.asyncio
async def test_request_raises_tracker_api_error(settings: Settings) -> None:
    respx.get("https://api.tracker.yandex.net/v3/myself").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized"})
    )

    client = TrackerClient(settings)
    with pytest.raises(TrackerAPIError) as exc:
        await client.request(method="GET", path="/v3/myself")

    assert exc.value.status_code == 401
    assert "Unauthorized" in exc.value.message


@respx.mock
@pytest.mark.asyncio
async def test_request_retries_once_on_503(settings: Settings) -> None:
    route = respx.get("https://api.tracker.yandex.net/v3/myself").mock(
        side_effect=[
            httpx.Response(503, json={"message": "temporary"}),
            httpx.Response(200, json={"uid": "1"}),
        ]
    )

    client = TrackerClient(settings)
    payload = await client.request(method="GET", path="/v3/myself")

    assert route.call_count == 2
    assert payload == {"uid": "1"}


@pytest.mark.asyncio
async def test_call_operation_requires_path_param(settings: Settings) -> None:
    client = TrackerClient(settings)
    operation = OperationSpec(
        operation_id="getIssue",
        domain="issue",
        action="get",
        method="GET",
        path="/v3/issues/{issue_id}",
        summary="Get issue",
    )

    with pytest.raises(TrackerConfigError):
        await client.call_operation(operation, path_params={})

