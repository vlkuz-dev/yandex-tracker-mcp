"""Pagination normalization helpers for Tracker API responses."""

from __future__ import annotations

from typing import Any

from .models import PaginatedEnvelope


def normalize_page(payload: Any) -> PaginatedEnvelope:
    """Normalize various paginated response shapes into a uniform envelope."""
    if isinstance(payload, list):
        return PaginatedEnvelope(
            results=payload,
            count=len(payload),
            next=None,
            prev=None,
        )

    if isinstance(payload, dict):
        if isinstance(payload.get("results"), list):
            results = payload["results"]
            count = _to_int(payload.get("count"), default=len(results))
            next_page = _to_optional_str(payload.get("next"))
            prev_page = _to_optional_str(payload.get("previous")) or _to_optional_str(
                payload.get("prev")
            )
            return PaginatedEnvelope(
                results=results,
                count=count,
                next=next_page,
                prev=prev_page,
            )

        if isinstance(payload.get("values"), list):
            results = payload["values"]
            count = _to_int(payload.get("total"), default=len(results))
            return PaginatedEnvelope(
                results=results,
                count=count,
                next=_to_optional_str(payload.get("next")),
                prev=_to_optional_str(payload.get("prev")),
            )

    return PaginatedEnvelope(results=[], count=0, next=None, prev=None)


def _to_int(value: Any, *, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return default


def _to_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
