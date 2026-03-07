"""Data structures shared by registry, tools and client layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

type HTTPMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
type JSONMapping = dict[str, Any]


@dataclass(slots=True, frozen=True)
class OperationSpec:
    """Describes a single typed Tracker API operation."""

    operation_id: str
    domain: str
    action: str
    method: HTTPMethod
    path: str
    summary: str
    paginated: bool = False
    typed_tool: bool = True

    @property
    def tool_name(self) -> str:
        return f"tracker_{self.domain}_{self.action}"


@dataclass(slots=True, frozen=True)
class RawGuardResult:
    method: HTTPMethod
    normalized_path: str


@dataclass(slots=True)
class PaginatedEnvelope:
    results: list[Any]
    count: int
    next: str | None
    prev: str | None

    def to_dict(self) -> JSONMapping:
        return {
            "results": self.results,
            "count": self.count,
            "next": self.next,
            "prev": self.prev,
        }
