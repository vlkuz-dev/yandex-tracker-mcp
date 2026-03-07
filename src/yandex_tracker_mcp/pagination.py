"""Pagination normalization helpers for Tracker API responses."""

from __future__ import annotations

from typing import Any

from .models import PaginatedEnvelope


def normalize_page(
    payload: Any, headers: dict[str, str] | None = None
) -> PaginatedEnvelope:
    """Normalize various paginated response shapes into a uniform envelope.

    When *headers* are provided, ``X-Total-Count`` is used as the
    authoritative total and ``Link`` header ``rel="next"`` signals
    more pages.
    """
    total = _header_int(headers, "x-total-count") if headers else None

    if isinstance(payload, list):
        has_more = _has_next_link(headers) if headers else False
        return PaginatedEnvelope(
            results=payload,
            total=total,
            count=len(payload),
            has_more=has_more,
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
            has_more = next_page is not None or (_has_next_link(headers) if headers else False)
            return PaginatedEnvelope(
                results=results,
                total=total if total is not None else count,
                count=len(results),
                has_more=has_more,
                next=next_page,
                prev=prev_page,
            )

        if isinstance(payload.get("values"), list):
            results = payload["values"]
            body_total = _to_int(payload.get("total"), default=len(results))
            next_page = _to_optional_str(payload.get("next"))
            has_more = next_page is not None or (_has_next_link(headers) if headers else False)
            return PaginatedEnvelope(
                results=results,
                total=total if total is not None else body_total,
                count=len(results),
                has_more=has_more,
                next=next_page,
                prev=_to_optional_str(payload.get("prev")),
            )

    return PaginatedEnvelope(
        results=[], total=total, count=0, has_more=False, next=None, prev=None
    )


def _header_int(headers: dict[str, str] | None, name: str) -> int | None:
    """Extract an integer from a response header (case-insensitive)."""
    if not headers:
        return None
    # httpx headers are case-insensitive but dict may not be
    for k, v in headers.items():
        if k.lower() == name.lower():
            return _to_int(v, default=0) or None
    return None


def _has_next_link(headers: dict[str, str] | None) -> bool:
    """Check whether the Link header contains rel=\"next\"."""
    if not headers:
        return False
    link = None
    for k, v in headers.items():
        if k.lower() == "link":
            link = v
            break
    if not link:
        return False
    return 'rel="next"' in link


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
