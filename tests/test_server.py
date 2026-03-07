from __future__ import annotations

import pytest

from yandex_tracker_mcp.config import Settings
from yandex_tracker_mcp.server import create_server


@pytest.fixture
def settings() -> Settings:
    return Settings.from_env(
        {
            "YANDEX_TRACKER_TOKEN": "token",
            "YANDEX_TRACKER_ORG_ID": "123",
            "YANDEX_TRACKER_BASE_URL": "https://api.tracker.yandex.net",
        }
    )


def test_create_server_has_lifespan(settings: Settings) -> None:
    from fastmcp.server.server import default_lifespan

    server = create_server(settings)
    assert server._lifespan is not default_lifespan


@pytest.mark.asyncio
async def test_create_server_registers_tools(settings: Settings) -> None:
    server = create_server(settings)
    tools = await server.list_tools()
    tool_names = [t.name for t in tools]
    assert "tracker_health" in tool_names
    assert "tracker_raw_request" in tool_names


@pytest.mark.asyncio
async def test_lifespan_starts_and_stops_client(settings: Settings) -> None:
    server = create_server(settings)
    lifespan_cm = server._lifespan(server)

    async with lifespan_cm as ctx:
        client = ctx["client"]
        assert client._http is not None
        assert not client._http.is_closed

    assert client._http is None
