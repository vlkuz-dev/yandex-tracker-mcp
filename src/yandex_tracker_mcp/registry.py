"""Operation registry for typed and raw tools."""

from __future__ import annotations

import json
import urllib.parse
from functools import lru_cache
from importlib import resources
from pathlib import PurePosixPath
from typing import Any, cast

from .errors import TrackerConfigError
from .models import HTTPMethod, OperationSpec, RawGuardResult

ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}

# Domain-level v3 guardrails for raw requests. This list intentionally includes
# broad stable sections from Tracker API to preserve coverage.
ALLOWED_V3_NAMESPACES = {
    "attachments",
    "boards",
    "bulkchange",
    "checklistItems",
    "checklists",
    "components",
    "dashboards",
    "fields",
    "filters",
    "groups",
    "issueTemplates",
    "issues",
    "issuetypes",
    "linktypes",
    "myself",
    "priorities",
    "projects",
    "projectTeams",
    "queues",
    "resolutions",
    "sprints",
    "statuses",
    "translations",
    "users",
    "versions",
    "workflows",
}


@lru_cache(maxsize=1)
def all_operations() -> tuple[OperationSpec, ...]:
    payload = _load_registry_json()
    specs: list[OperationSpec] = []
    for row in payload:
        specs.append(
            OperationSpec(
                operation_id=str(row["operation_id"]),
                domain=str(row["domain"]),
                action=str(row["action"]),
                method=_normalize_method(str(row["method"])),
                path=str(row["path"]),
                summary=str(row["summary"]),
                paginated=bool(row.get("paginated", False)),
                typed_tool=bool(row.get("typed_tool", True)),
            )
        )
    _validate_registry(specs)
    return tuple(specs)


@lru_cache(maxsize=1)
def operations_by_id() -> dict[str, OperationSpec]:
    return {operation.operation_id: operation for operation in all_operations()}


def typed_operations() -> tuple[OperationSpec, ...]:
    return tuple(operation for operation in all_operations() if operation.typed_tool)


def get_operation(operation_id: str) -> OperationSpec:
    try:
        return operations_by_id()[operation_id]
    except KeyError as exc:
        raise TrackerConfigError(f"Unknown operation_id: {operation_id}") from exc


def validate_raw_request(method: str, path: str) -> RawGuardResult:
    normalized_method = _normalize_method(method)
    if normalized_method not in ALLOWED_METHODS:
        raise TrackerConfigError(
            f"Unsupported method for raw request. Allowed: {sorted(ALLOWED_METHODS)}"
        )

    normalized_path = _normalize_path(path)
    decoded_path = _fully_decode(normalized_path)
    parts = [part for part in PurePosixPath(decoded_path).parts if part not in {"/", ""}]

    if ".." in parts:
        raise TrackerConfigError("Path traversal segments ('..') are not allowed")

    if len(parts) < 2 or parts[0] != "v3":
        raise TrackerConfigError("Raw requests are limited to /v3/* paths")

    namespace = parts[1]
    if namespace not in ALLOWED_V3_NAMESPACES:
        raise TrackerConfigError(
            f"Raw request path is outside allowed v3 namespaces: {namespace!r}"
        )

    return RawGuardResult(method=normalized_method, normalized_path=decoded_path)


def _fully_decode(path: str) -> str:
    """Decode percent-encoded characters repeatedly until stable.

    Prevents double-encoding bypasses like ``%252e%252e`` which a single
    ``urllib.parse.unquote`` call would leave as ``%2e%2e``.
    """
    previous = path
    while True:
        decoded = urllib.parse.unquote(previous)
        if decoded == previous:
            return decoded
        previous = decoded


def _normalize_path(path: str) -> str:
    value = path.strip()
    if not value:
        raise TrackerConfigError("Request path must be non-empty")
    if not value.startswith("/"):
        value = f"/{value}"
    return value


def _normalize_method(method: str) -> HTTPMethod:
    normalized = method.strip().upper()
    if normalized not in ALLOWED_METHODS:
        raise TrackerConfigError(f"Unsupported HTTP method: {method!r}")
    return cast(HTTPMethod, normalized)


def _load_registry_json() -> list[dict[str, Any]]:
    raw = (
        resources.files("yandex_tracker_mcp")
        .joinpath("operations.json")
        .read_text(encoding="utf-8")
    )
    data = json.loads(raw)
    if not isinstance(data, list):
        raise TrackerConfigError("operations.json must contain a list")
    return [dict(item) for item in data]


def _validate_registry(specs: list[OperationSpec]) -> None:
    if not specs:
        raise TrackerConfigError("Operation registry is empty")

    seen_op_ids: set[str] = set()
    seen_tools: set[str] = set()

    for spec in specs:
        if spec.operation_id in seen_op_ids:
            raise TrackerConfigError(f"Duplicate operation_id in registry: {spec.operation_id}")
        seen_op_ids.add(spec.operation_id)

        if spec.method not in ALLOWED_METHODS:
            raise TrackerConfigError(f"Invalid HTTP method {spec.method!r} in {spec.operation_id}")

        if not spec.path.startswith("/v3/") and spec.path != "/v3/myself":
            raise TrackerConfigError(
                f"Operation path must be /v3/* in {spec.operation_id}: {spec.path}"
            )

        if spec.typed_tool:
            if spec.tool_name in seen_tools:
                raise TrackerConfigError(f"Duplicate typed tool name in registry: {spec.tool_name}")
            seen_tools.add(spec.tool_name)
