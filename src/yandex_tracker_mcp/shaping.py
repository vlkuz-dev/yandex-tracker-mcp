"""Response shaping: compact nested Tracker objects for LLM consumption."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

# Fields to keep in compacted issue representations.
ISSUE_KEEP_FIELDS: set[str] = {
    "self",
    "key",
    "summary",
    "description",
    "status",
    "type",
    "priority",
    "assignee",
    "createdBy",
    "updatedBy",
    "createdAt",
    "updatedAt",
    "deadline",
    "resolution",
    "tags",
    "components",
    "sprint",
    "parent",
    "queue",
    "followers",
    "start",
    "end",
    "storyPoints",
}

# Fields excluded from list/paginated responses (too verbose for summaries).
_LIST_EXCLUDE_FIELDS: set[str] = {
    "description",
    "followers",
    "self",
    "createdBy",
    "updatedBy",
    "createdAt",
    "updatedAt",
}

# Nested objects flattened to their ``display`` value.
_FLATTEN_TO_DISPLAY: set[str] = {
    "status",
    "type",
    "priority",
    "assignee",
    "createdBy",
    "updatedBy",
    "resolution",
    "sprint",
}

# Nested objects flattened to their ``key`` value.
_FLATTEN_TO_KEY: set[str] = {"parent", "queue"}

type Shaper = Callable[[dict[str, Any]], dict[str, Any]]


def _flatten_value(key: str, value: Any) -> Any:
    """Flatten a single field value according to shaping rules."""
    if not isinstance(value, dict):
        if isinstance(value, list):
            return [_flatten_value(key, item) for item in value]
        return value

    if key in _FLATTEN_TO_DISPLAY:
        return value.get("display", value)
    if key in _FLATTEN_TO_KEY:
        return value.get("key", value)

    # User-like objects in lists (e.g. followers)
    if "display" in value and "id" in value and len(value) >= 3:
        return value.get("display")

    return value


def compact_issue(issue: dict[str, Any], *, for_list: bool = False) -> dict[str, Any]:
    """Return a compacted copy of an issue dict.

    * Drops fields not in ``ISSUE_KEEP_FIELDS``
    * Flattens nested objects (users → display name, queue/parent → key)
    * When *for_list* is True, additionally strips verbose fields
      (description, followers, timestamps, etc.) for concise listings.
    """
    fields = ISSUE_KEEP_FIELDS - _LIST_EXCLUDE_FIELDS if for_list else ISSUE_KEEP_FIELDS
    result: dict[str, Any] = {}
    for key in fields:
        if key not in issue:
            continue
        result[key] = _flatten_value(key, issue[key])
    return result


# ---------------------------------------------------------------------------
# Domain → shaper mapping
# ---------------------------------------------------------------------------

_ISSUE_DOMAINS: set[str] = {"issue", "issues"}


def _compact_issue_for_list(issue: dict[str, Any]) -> dict[str, Any]:
    return compact_issue(issue, for_list=True)


def get_shaper(domain: str, *, for_list: bool = False) -> Shaper | None:
    """Return a shaping function for the given operation domain, or None."""
    if domain in _ISSUE_DOMAINS:
        return _compact_issue_for_list if for_list else compact_issue
    return None
