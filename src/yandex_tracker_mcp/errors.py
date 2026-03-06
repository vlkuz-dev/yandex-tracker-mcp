"""Error model for Tracker API and server configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class TrackerConfigError(ValueError):
    """Raised when MCP server configuration is invalid."""


@dataclass(slots=True)
class TrackerAPIError(Exception):
    """Represents an HTTP error returned by Tracker API."""

    status_code: int
    message: str
    details: dict[str, Any] | None = None

    def __str__(self) -> str:
        if self.details:
            return f"Tracker API error {self.status_code}: {self.message} ({self.details})"
        return f"Tracker API error {self.status_code}: {self.message}"

