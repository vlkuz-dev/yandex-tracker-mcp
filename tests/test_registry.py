from __future__ import annotations

import pytest

from yandex_tracker_mcp.errors import TrackerConfigError
from yandex_tracker_mcp.registry import all_operations, typed_operations, validate_raw_request


def test_operations_registry_not_empty() -> None:
    assert len(all_operations()) > 0
    assert len(typed_operations()) > 0


def test_validate_raw_request_allows_v3_issue_namespace() -> None:
    result = validate_raw_request(method="get", path="/v3/issues/TEST-1")
    assert result.method == "GET"
    assert result.normalized_path == "/v3/issues/TEST-1"


def test_validate_raw_request_rejects_non_v3() -> None:
    with pytest.raises(TrackerConfigError):
        validate_raw_request(method="GET", path="/v2/issues")


def test_validate_raw_request_rejects_unknown_namespace() -> None:
    with pytest.raises(TrackerConfigError):
        validate_raw_request(method="GET", path="/v3/admin/settings")


def test_validate_raw_request_rejects_path_traversal() -> None:
    with pytest.raises(TrackerConfigError, match="Path traversal"):
        validate_raw_request(method="GET", path="/v3/issues/../../../admin")
