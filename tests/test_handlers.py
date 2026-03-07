"""Tests for the handlers module (build_typed_handler)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from yandex_tracker_mcp.handlers import build_typed_handler
from yandex_tracker_mcp.models import OperationSpec


def _make_operation(*, paginated: bool = False) -> OperationSpec:
    return OperationSpec(
        operation_id="issue_get",
        domain="issue",
        action="get",
        method="GET",
        path="/v3/issues/{issueKey}",
        summary="Get an issue by key.",
        paginated=paginated,
    )


def _make_paginated_operation() -> OperationSpec:
    return OperationSpec(
        operation_id="issues_find",
        domain="issues",
        action="find",
        method="POST",
        path="/v3/issues/_search",
        summary="Find issues by filter.",
        paginated=True,
    )


def _mock_client(response: Any) -> AsyncMock:
    client = AsyncMock()
    client.call_operation = AsyncMock(return_value=response)
    return client


class TestBuildTypedHandler:
    """Tests for build_typed_handler callable construction."""

    def test_creates_callable_with_correct_name(self) -> None:
        operation = _make_operation()
        client = _mock_client({})
        handler = build_typed_handler(client, operation)
        assert handler.__name__ == "tool_issue_get"

    def test_creates_callable_with_correct_doc(self) -> None:
        operation = _make_operation()
        client = _mock_client({})
        handler = build_typed_handler(client, operation)
        assert handler.__doc__ == "Get an issue by key."

    def test_handler_is_callable(self) -> None:
        operation = _make_operation()
        client = _mock_client({})
        handler = build_typed_handler(client, operation)
        assert callable(handler)


class TestNonPaginatedHandler:
    """Tests for non-paginated handler response envelope structure."""

    @pytest.mark.asyncio
    async def test_returns_operation_metadata(self) -> None:
        operation = _make_operation(paginated=False)
        api_data = {"key": "PROJ-1", "summary": "Test issue"}
        client = _mock_client(api_data)

        handler = build_typed_handler(client, operation)
        result = await handler(path_params={"issueKey": "PROJ-1"})

        assert result["operation_id"] == "issue_get"
        assert result["tool_name"] == "tracker_issue_get"
        assert result["method"] == "GET"
        assert result["path_template"] == "/v3/issues/{issueKey}"
        assert result["data"] == api_data

    @pytest.mark.asyncio
    async def test_passes_params_to_client(self) -> None:
        operation = _make_operation(paginated=False)
        client = _mock_client({"key": "PROJ-1"})

        handler = build_typed_handler(client, operation)
        await handler(
            path_params={"issueKey": "PROJ-1"},
            query={"expand": "transitions"},
            body=None,
        )

        client.call_operation.assert_awaited_once_with(
            operation,
            path_params={"issueKey": "PROJ-1"},
            query={"expand": "transitions"},
            body=None,
        )

    @pytest.mark.asyncio
    async def test_envelope_has_exactly_expected_keys(self) -> None:
        operation = _make_operation(paginated=False)
        client = _mock_client({"key": "X-1"})

        handler = build_typed_handler(client, operation)
        result = await handler()

        expected_keys = {"operation_id", "tool_name", "method", "path_template", "data"}
        assert set(result.keys()) == expected_keys


class TestPaginatedHandler:
    """Tests for paginated handler response envelope structure."""

    @pytest.mark.asyncio
    async def test_returns_paginated_envelope(self) -> None:
        operation = _make_paginated_operation()
        api_data = [{"key": "PROJ-1"}, {"key": "PROJ-2"}]
        client = _mock_client(api_data)

        handler = build_typed_handler(client, operation)
        result = await handler(body={"filter": {}})

        assert result["results"] == api_data
        assert result["count"] == 2
        assert result["next"] is None
        assert result["prev"] is None

    @pytest.mark.asyncio
    async def test_paginated_dict_response(self) -> None:
        operation = _make_paginated_operation()
        api_data = {
            "results": [{"key": "A-1"}],
            "count": 10,
            "next": "/v3/issues/_search?page=2",
        }
        client = _mock_client(api_data)

        handler = build_typed_handler(client, operation)
        result = await handler()

        assert result["results"] == [{"key": "A-1"}]
        assert result["count"] == 10
        assert result["next"] == "/v3/issues/_search?page=2"
