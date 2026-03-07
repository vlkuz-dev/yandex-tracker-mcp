"""Typed handler construction for Tracker tool operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .client import TrackerClient
from .models import OperationSpec
from .pagination import normalize_page


def build_typed_handler(
    client: TrackerClient, operation: OperationSpec
) -> Callable[
    [dict[str, Any] | None, dict[str, Any] | None, Any | None], Awaitable[dict[str, Any]]
]:
    """Build an async handler for a typed Tracker operation.

    For paginated operations the response is normalized into a
    ``PaginatedEnvelope``.  Non-paginated operations return an
    info-envelope with operation metadata alongside the raw data.
    """

    async def _handler(
        path_params: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
    ) -> dict[str, Any]:
        response = await client.call_operation(
            operation,
            path_params=path_params,
            query=query,
            body=body,
        )
        if operation.paginated:
            page = normalize_page(response)
            return page.to_dict()
        return {
            "operation_id": operation.operation_id,
            "tool_name": operation.tool_name,
            "method": operation.method,
            "path_template": operation.path,
            "data": response,
        }

    _handler.__name__ = f"tool_{operation.domain}_{operation.action}"
    _handler.__doc__ = operation.summary
    return _handler
