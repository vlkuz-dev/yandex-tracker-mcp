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

    async with TrackerClient(settings) as client:
        payload = await client.request(method="GET", path="/v3/myself")

    assert route.called
    assert payload == {"uid": "1"}


@respx.mock
@pytest.mark.asyncio
async def test_request_raises_tracker_api_error(settings: Settings) -> None:
    respx.get("https://api.tracker.yandex.net/v3/myself").mock(
        return_value=httpx.Response(401, json={"message": "Unauthorized"})
    )

    async with TrackerClient(settings) as client:
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

    async with TrackerClient(settings) as client:
        payload = await client.request(method="GET", path="/v3/myself")

    assert route.call_count == 2
    assert payload == {"uid": "1"}


@pytest.mark.asyncio
async def test_call_operation_requires_path_param(settings: Settings) -> None:
    async with TrackerClient(settings) as client:
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


# --- Lifecycle tests ---


@pytest.mark.asyncio
async def test_start_creates_http_client(settings: Settings) -> None:
    client = TrackerClient(settings)
    assert client._http is None

    await client.start()
    assert client._http is not None
    assert isinstance(client._http, httpx.AsyncClient)

    await client.stop()


@pytest.mark.asyncio
async def test_stop_closes_http_client(settings: Settings) -> None:
    client = TrackerClient(settings)
    await client.start()
    http = client._http
    assert http is not None

    await client.stop()
    assert client._http is None
    assert http.is_closed


@pytest.mark.asyncio
async def test_request_raises_before_start(settings: Settings) -> None:
    client = TrackerClient(settings)
    with pytest.raises(TrackerConfigError, match="not started"):
        await client.request(method="GET", path="/v3/myself")


@pytest.mark.asyncio
async def test_request_raises_after_stop(settings: Settings) -> None:
    client = TrackerClient(settings)
    await client.start()
    await client.stop()

    with pytest.raises(TrackerConfigError, match="not started"):
        await client.request(method="GET", path="/v3/myself")


@pytest.mark.asyncio
async def test_context_manager(settings: Settings) -> None:
    client = TrackerClient(settings)
    async with client:
        assert client._http is not None
    assert client._http is None


@pytest.mark.asyncio
async def test_start_is_idempotent(settings: Settings) -> None:
    client = TrackerClient(settings)
    await client.start()
    first_http = client._http
    await client.start()
    assert client._http is first_http
    await client.stop()


@pytest.mark.asyncio
async def test_request_wraps_closed_client_error(settings: Settings) -> None:
    client = TrackerClient(settings)
    await client.start()
    # Close the underlying httpx client to simulate shutdown during request
    await client._http.aclose()

    with pytest.raises(TrackerAPIError) as exc:
        await client.request(method="GET", path="/v3/myself")

    assert exc.value.status_code == 0
    assert "closed" in exc.value.message.lower()

    # Clean up (client._http is still set but closed)
    client._http = None


@respx.mock
@pytest.mark.asyncio
async def test_persistent_client_reused_across_requests(settings: Settings) -> None:
    respx.get("https://api.tracker.yandex.net/v3/myself").mock(
        return_value=httpx.Response(200, json={"uid": "1"})
    )

    async with TrackerClient(settings) as client:
        http_before = client._http
        await client.request(method="GET", path="/v3/myself")
        await client.request(method="GET", path="/v3/myself")
        assert client._http is http_before
