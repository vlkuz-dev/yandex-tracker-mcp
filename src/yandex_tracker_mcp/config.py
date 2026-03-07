"""Runtime configuration and auth header builder."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from .errors import TrackerConfigError

DEFAULT_BASE_URL = "https://api.tracker.yandex.net"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_RETRIES = 2
DEFAULT_USER_AGENT = "yandex-tracker-mcp/0.1.0"
SUPPORTED_TOKEN_TYPES = {"OAuth", "Bearer"}


@dataclass(slots=True, frozen=True)
class Settings:
    token: str
    token_type: str
    org_id: str | None
    cloud_org_id: str | None
    base_url: str
    timeout_seconds: float
    retries: int
    user_agent: str

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        source = dict(os.environ if env is None else env)

        token = source.get("YANDEX_TRACKER_TOKEN", "").strip()
        if not token:
            raise TrackerConfigError("YANDEX_TRACKER_TOKEN is required")

        token_type = source.get("YANDEX_TRACKER_TOKEN_TYPE", "OAuth").strip() or "OAuth"
        if token_type not in SUPPORTED_TOKEN_TYPES:
            raise TrackerConfigError("YANDEX_TRACKER_TOKEN_TYPE must be one of: OAuth, Bearer")

        org_id = _normalize_optional(source.get("YANDEX_TRACKER_ORG_ID"))
        cloud_org_id = _normalize_optional(source.get("YANDEX_TRACKER_CLOUD_ORG_ID"))

        if bool(org_id) == bool(cloud_org_id):
            raise TrackerConfigError(
                "Set exactly one of YANDEX_TRACKER_ORG_ID or YANDEX_TRACKER_CLOUD_ORG_ID"
            )

        base_url = source.get("YANDEX_TRACKER_BASE_URL", DEFAULT_BASE_URL).strip()
        if not base_url.startswith("https://"):
            raise TrackerConfigError("YANDEX_TRACKER_BASE_URL must start with https://")

        timeout_seconds = _parse_float(
            source.get("YANDEX_TRACKER_TIMEOUT_SECONDS"),
            default=DEFAULT_TIMEOUT_SECONDS,
            name="YANDEX_TRACKER_TIMEOUT_SECONDS",
        )
        retries = _parse_int(
            source.get("YANDEX_TRACKER_RETRIES"),
            default=DEFAULT_RETRIES,
            name="YANDEX_TRACKER_RETRIES",
        )
        if retries < 0:
            raise TrackerConfigError("YANDEX_TRACKER_RETRIES must be >= 0")

        user_agent = source.get("YANDEX_TRACKER_USER_AGENT", DEFAULT_USER_AGENT).strip()
        if not user_agent:
            user_agent = DEFAULT_USER_AGENT

        return cls(
            token=token,
            token_type=token_type,
            org_id=org_id,
            cloud_org_id=cloud_org_id,
            base_url=base_url.rstrip("/"),
            timeout_seconds=timeout_seconds,
            retries=retries,
            user_agent=user_agent,
        )

    def headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"{self.token_type} {self.token}",
            "Accept": "application/json",
            "User-Agent": self.user_agent,
        }
        if self.org_id:
            headers["X-Org-ID"] = self.org_id
        if self.cloud_org_id:
            headers["X-Cloud-Org-ID"] = self.cloud_org_id
        return headers


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _parse_float(raw: str | None, *, default: float, name: str) -> float:
    if raw is None or raw == "":
        return default
    try:
        parsed = float(raw)
    except ValueError as exc:
        raise TrackerConfigError(f"{name} must be a float") from exc
    if parsed <= 0:
        raise TrackerConfigError(f"{name} must be > 0")
    return parsed


def _parse_int(raw: str | None, *, default: int, name: str) -> int:
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise TrackerConfigError(f"{name} must be an integer") from exc
