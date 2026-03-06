"""FastMCP server factory."""

from __future__ import annotations

from fastmcp import FastMCP

from .client import TrackerClient
from .config import Settings
from .tools import register_tools


def create_server(settings: Settings | None = None) -> FastMCP:
    runtime_settings = settings or Settings.from_env()
    client = TrackerClient(runtime_settings)

    server = FastMCP(name="yandex-tracker", instructions=_instructions())
    register_tools(server, client)
    return server


def _instructions() -> str:
    return (
        "Use typed tracker_* tools for standard operations whenever possible. "
        "Use tracker_raw_request for uncovered v3 endpoints. "
        "Respect Yandex Tracker API v3 parameter and field naming."
    )

