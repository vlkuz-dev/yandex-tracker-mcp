"""FastMCP tool registration for Tracker operations."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from .client import TrackerClient
from .handlers import build_typed_handler
from .registry import typed_operations, validate_raw_request


def register_tools(server: FastMCP, client: TrackerClient) -> None:
    register_health_tool(server)
    register_registry_tool(server)
    register_raw_tool(server, client)
    register_typed_tools(server, client)


def register_health_tool(server: FastMCP) -> None:
    @server.tool(name="tracker_health")
    async def tracker_health() -> dict[str, Any]:
        """Get service status and supported mode."""
        return {"status": "ok", "service": "yandex-tracker-mcp", "api": "v3"}


def register_registry_tool(server: FastMCP) -> None:
    @server.tool(name="tracker_list_supported_operations")
    async def tracker_list_supported_operations() -> dict[str, Any]:
        """List typed operations currently exposed by this MCP server."""
        operations: list[dict[str, Any]] = []
        for operation in typed_operations():
            operations.append(
                {
                    "operation_id": operation.operation_id,
                    "tool_name": operation.tool_name,
                    "method": operation.method,
                    "path": operation.path,
                    "summary": operation.summary,
                    "paginated": operation.paginated,
                }
            )
        return {"count": len(operations), "results": operations}


def register_raw_tool(server: FastMCP, client: TrackerClient) -> None:
    @server.tool(name="tracker_raw_request")
    async def tracker_raw_request(
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
    ) -> dict[str, Any]:
        """Run a raw Tracker API v3 request restricted to allowed namespaces."""
        guard = validate_raw_request(method=method, path=path)
        data = await client.request(
            method=guard.method,
            path=guard.normalized_path,
            query=query,
            body=body,
        )
        return {
            "method": guard.method,
            "path": guard.normalized_path,
            "data": data,
        }


def register_typed_tools(server: FastMCP, client: TrackerClient) -> None:
    for operation in typed_operations():
        handler = build_typed_handler(client, operation)
        server.tool(name=operation.tool_name)(handler)
