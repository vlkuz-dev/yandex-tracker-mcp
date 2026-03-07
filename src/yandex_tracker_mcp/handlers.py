"""Typed handler construction for Tracker tool operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from .client import TrackerClient
from .models import OperationSpec
from .pagination import normalize_page
from .shaping import get_shaper

DEFAULT_PAGE_SIZE = 10


def build_typed_handler(
    client: TrackerClient, operation: OperationSpec
) -> Callable[
    [dict[str, Any] | None, dict[str, Any] | None, Any | None], Awaitable[Any]
]:
    """Build an async handler for a typed Tracker operation.

    For paginated operations the response is normalized into a
    ``PaginatedEnvelope``.  Non-paginated operations return the
    API response directly.
    """

    shaper = get_shaper(operation.domain)

    async def _handler(
        path_params: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: Any | None = None,
    ) -> Any:
        if operation.paginated:
            query = dict(query or {})
            if "perPage" not in query:
                query["perPage"] = DEFAULT_PAGE_SIZE

        compact = True
        if query and "_compact" in query:
            compact = bool(query.pop("_compact", True))
            if not query:
                query = None

        response = await client.call_operation(
            operation,
            path_params=path_params,
            query=query,
            body=body,
            include_headers=operation.paginated,
        )
        if operation.paginated:
            body_data, headers = response
            page = normalize_page(body_data, headers)
            if compact and shaper:
                page.results = [shaper(item) for item in page.results]
            return page.to_dict()
        if compact and shaper and isinstance(response, dict):
            return shaper(response)
        return response

    _handler.__name__ = f"tool_{operation.domain}_{operation.action}"
    _handler.__doc__ = operation.summary
    return _handler
