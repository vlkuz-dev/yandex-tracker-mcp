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


def _paginated_response(
    body: Any, *, total: int | None = None, has_next: bool = False
) -> tuple[Any, dict[str, str]]:
    """Build a (body, headers) tuple as returned by include_headers=True."""
    headers: dict[str, str] = {}
    if total is not None:
        headers["x-total-count"] = str(total)
    if has_next:
        headers["link"] = '<https://example.com?page=2>; rel="next"'
    return body, headers


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
    """Tests for non-paginated handler response structure."""

    @pytest.mark.asyncio
    async def test_returns_api_response_directly(self) -> None:
        operation = _make_operation(paginated=False)
        api_data = {"key": "PROJ-1", "summary": "Test issue"}
        client = _mock_client(api_data)

        handler = build_typed_handler(client, operation)
        result = await handler(path_params={"issueKey": "PROJ-1"})

        assert result == api_data

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
            include_headers=False,
        )


class TestPaginatedHandler:
    """Tests for paginated handler response envelope structure."""

    @pytest.mark.asyncio
    async def test_returns_paginated_envelope(self) -> None:
        operation = _make_paginated_operation()
        api_data = [{"key": "PROJ-1"}, {"key": "PROJ-2"}]
        client = _mock_client(_paginated_response(api_data, total=2))

        handler = build_typed_handler(client, operation)
        result = await handler(body={"filter": {}})

        assert result["count"] == 2
        assert result["total"] == 2
        assert result["has_more"] is False

    @pytest.mark.asyncio
    async def test_paginated_with_more_pages(self) -> None:
        operation = _make_paginated_operation()
        api_data = [{"key": "A-1"}]
        client = _mock_client(_paginated_response(api_data, total=25, has_next=True))

        handler = build_typed_handler(client, operation)
        result = await handler()

        assert result["count"] == 1
        assert result["total"] == 25
        assert result["has_more"] is True

    @pytest.mark.asyncio
    async def test_paginated_dict_response(self) -> None:
        operation = _make_paginated_operation()
        api_data = {
            "results": [{"key": "A-1"}],
            "count": 10,
            "next": "/v3/issues/_search?page=2",
        }
        client = _mock_client(_paginated_response(api_data, total=10))

        handler = build_typed_handler(client, operation)
        result = await handler()

        assert result["results"] == [{"key": "A-1"}]
        assert result["count"] == 1
        assert result["total"] == 10
        assert result["has_more"] is True

    @pytest.mark.asyncio
    async def test_injects_default_per_page(self) -> None:
        operation = _make_paginated_operation()
        client = _mock_client(_paginated_response([]))

        handler = build_typed_handler(client, operation)
        await handler(body={"filter": {}})

        call_kwargs = client.call_operation.call_args[1]
        assert call_kwargs["query"]["perPage"] == 10

    @pytest.mark.asyncio
    async def test_preserves_user_per_page(self) -> None:
        operation = _make_paginated_operation()
        client = _mock_client(_paginated_response([]))

        handler = build_typed_handler(client, operation)
        await handler(query={"perPage": 50}, body={"filter": {}})

        call_kwargs = client.call_operation.call_args[1]
        assert call_kwargs["query"]["perPage"] == 50


class TestShapingIntegration:
    """Tests for response shaping in handlers."""

    @pytest.mark.asyncio
    async def test_non_paginated_issue_is_compacted(self) -> None:
        operation = _make_operation(paginated=False)
        api_data = {
            "key": "PROJ-1",
            "summary": "Test",
            "votes": 5,
            "favorite": True,
            "status": {"id": "1", "key": "open", "display": "Open", "self": "..."},
        }
        client = _mock_client(api_data)

        handler = build_typed_handler(client, operation)
        result = await handler(path_params={"issueKey": "PROJ-1"})

        assert result["key"] == "PROJ-1"
        assert result["status"] == "Open"
        assert "votes" not in result
        assert "favorite" not in result

    @pytest.mark.asyncio
    async def test_paginated_issues_are_compacted(self) -> None:
        operation = _make_paginated_operation()
        api_data = [
            {
                "key": "PROJ-1",
                "summary": "A",
                "description": "Long description text",
                "votes": 3,
                "status": {"id": "1", "key": "open", "display": "Open", "self": "..."},
            },
        ]
        client = _mock_client(_paginated_response(api_data, total=1))

        handler = build_typed_handler(client, operation)
        result = await handler(body={"filter": {}})

        item = result["results"][0]
        assert item["key"] == "PROJ-1"
        assert item["status"] == "Open"
        assert "votes" not in item
        assert "description" not in item  # excluded in list mode

    @pytest.mark.asyncio
    async def test_non_paginated_issue_keeps_description(self) -> None:
        operation = _make_operation(paginated=False)
        api_data = {
            "key": "PROJ-1",
            "summary": "Test",
            "description": "Important details",
        }
        client = _mock_client(api_data)

        handler = build_typed_handler(client, operation)
        result = await handler(path_params={"issueKey": "PROJ-1"})

        assert result["description"] == "Important details"

    @pytest.mark.asyncio
    async def test_compact_false_skips_shaping(self) -> None:
        operation = _make_operation(paginated=False)
        api_data = {
            "key": "PROJ-1",
            "summary": "Test",
            "votes": 5,
            "favorite": True,
        }
        client = _mock_client(api_data)

        handler = build_typed_handler(client, operation)
        result = await handler(query={"_compact": False})

        assert result == api_data

    @pytest.mark.asyncio
    async def test_compact_false_paginated_skips_shaping(self) -> None:
        operation = _make_paginated_operation()
        raw_issue = {"key": "PROJ-1", "votes": 10, "favorite": True}
        client = _mock_client(_paginated_response([raw_issue]))

        handler = build_typed_handler(client, operation)
        result = await handler(query={"_compact": False}, body={})

        assert result["results"][0]["votes"] == 10

    @pytest.mark.asyncio
    async def test_compact_param_not_sent_to_api(self) -> None:
        operation = _make_operation(paginated=False)
        client = _mock_client({"key": "X-1"})

        handler = build_typed_handler(client, operation)
        await handler(query={"_compact": False, "expand": "transitions"})

        call_kwargs = client.call_operation.call_args[1]
        assert "_compact" not in call_kwargs["query"]
        assert call_kwargs["query"]["expand"] == "transitions"

    @pytest.mark.asyncio
    async def test_non_issue_domain_not_compacted(self) -> None:
        operation = OperationSpec(
            operation_id="queue_get",
            domain="queue",
            action="get_metadata",
            method="GET",
            path="/v3/queues/{queue_id}",
            summary="Get queue metadata",
        )
        api_data = {"id": "q1", "key": "PROJ", "extra_field": "kept"}
        client = _mock_client(api_data)

        handler = build_typed_handler(client, operation)
        result = await handler()

        assert result == api_data

    @pytest.mark.asyncio
    async def test_comments_use_comment_shaper(self) -> None:
        operation = OperationSpec(
            operation_id="getIssueComments",
            domain="issue",
            action="get_comments",
            method="GET",
            path="/v3/issues/{issue_id}/comments/",
            summary="Get issue comments",
            paginated=True,
        )
        raw_comment = {
            "id": 123,
            "text": "Please approve",
            "createdBy": {"id": "u1", "display": "Alice", "self": "..."},
            "longId": "abc123",
            "version": 1,
            "self": "https://...",
        }
        client = _mock_client(_paginated_response([raw_comment], total=1))

        handler = build_typed_handler(client, operation)
        result = await handler(path_params={"issue_id": "X-1"})

        item = result["results"][0]
        assert item["text"] == "Please approve"
        assert item["createdBy"] == "Alice"
        assert "longId" not in item
        assert "version" not in item
        assert "self" not in item

    @pytest.mark.asyncio
    async def test_transitions_pass_through(self) -> None:
        operation = OperationSpec(
            operation_id="getIssueTransitions",
            domain="issue",
            action="get_transitions",
            method="GET",
            path="/v3/issues/{issue_id}/transitions/",
            summary="Get issue transitions",
        )
        api_data = [{"id": "1", "display": "Close", "to": {"key": "closed"}}]
        client = _mock_client(api_data)

        handler = build_typed_handler(client, operation)
        result = await handler(path_params={"issue_id": "X-1"})

        assert result == api_data
