"""Async HTTP client wrapper for Tracker API."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from .config import Settings
from .errors import TrackerAPIError, TrackerConfigError
from .models import JSONMapping, OperationSpec

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_PATH_PARAM_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


class TrackerClient:
    """Thin async client with retries and typed operation execution."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http: httpx.AsyncClient | None = None

    async def start(self) -> None:
        """Create the persistent httpx.AsyncClient with connection pooling."""
        if self._http is not None:
            return
        self._http = httpx.AsyncClient(
            headers=self._settings.headers(),
            timeout=httpx.Timeout(self._settings.timeout_seconds),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    async def stop(self) -> None:
        """Close the underlying httpx.AsyncClient."""
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def __aenter__(self) -> TrackerClient:
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()

    def _ensure_started(self) -> httpx.AsyncClient:
        if self._http is None:
            raise TrackerConfigError("TrackerClient is not started; call start() first")
        return self._http

    async def request(
        self,
        *,
        method: str,
        path: str,
        query: JSONMapping | None = None,
        body: Any | None = None,
    ) -> Any:
        http = self._ensure_started()
        url = f"{self._settings.base_url}{path}"

        attempt = 0
        while True:
            attempt += 1
            try:
                response = await http.request(
                    method=method,
                    url=url,
                    params=query,
                    json=body,
                )
            except httpx.RequestError as exc:
                if attempt > self._settings.retries + 1:
                    raise TrackerAPIError(
                        status_code=0,
                        message="Network request to Tracker API failed",
                        details={"error": str(exc)},
                    ) from exc
                await asyncio.sleep(_retry_delay(attempt))
                continue

            if response.status_code in RETRYABLE_STATUS_CODES and attempt <= self._settings.retries:
                await asyncio.sleep(_retry_delay(attempt))
                continue

            if response.status_code >= 400:
                raise _build_api_error(response)

            if response.status_code == 204:
                return {"ok": True, "status_code": response.status_code}

            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            return {"raw": response.text, "status_code": response.status_code}

    async def call_operation(
        self,
        operation: OperationSpec,
        *,
        path_params: JSONMapping | None = None,
        query: JSONMapping | None = None,
        body: Any | None = None,
    ) -> Any:
        built_path = _build_path(operation.path, path_params)
        return await self.request(method=operation.method, path=built_path, query=query, body=body)


def _build_path(path_template: str, path_params: JSONMapping | None) -> str:
    params = {} if path_params is None else path_params

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in params:
            raise TrackerConfigError(f"Missing path parameter: {key}")
        raw_value = params[key]
        if raw_value is None:
            raise TrackerConfigError(f"Path parameter cannot be null: {key}")
        return str(raw_value)

    built = _PATH_PARAM_RE.sub(replace, path_template)
    if "{" in built or "}" in built:
        raise TrackerConfigError(f"Unresolved path template after substitution: {built}")
    return built


def _retry_delay(attempt: int) -> float:
    # Bounded exponential backoff to protect API and keep latency predictable.
    return float(min(2.0, 0.25 * (2 ** (attempt - 1))))


def _build_api_error(response: httpx.Response) -> TrackerAPIError:
    payload: dict[str, Any] | None = None
    message = f"HTTP {response.status_code}"

    try:
        candidate = response.json()
    except ValueError:
        candidate = None

    if isinstance(candidate, dict):
        payload = candidate
        for key in ("message", "errorMessages", "description", "error"):
            value = candidate.get(key)
            if isinstance(value, str) and value:
                message = value
                break
            if isinstance(value, list) and value:
                message = ", ".join(str(item) for item in value)
                break
    elif response.text:
        message = response.text[:500]

    return TrackerAPIError(status_code=response.status_code, message=message, details=payload)
