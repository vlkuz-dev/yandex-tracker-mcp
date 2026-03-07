"""Response shaping: compact nested Tracker objects for LLM consumption."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

type Shaper = Callable[[dict[str, Any]], dict[str, Any]]

# ---------------------------------------------------------------------------
# Flatten helpers
# ---------------------------------------------------------------------------

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

    # User-like objects in lists (e.g. followers, summonees)
    if "display" in value and "id" in value and len(value) >= 3:
        return value.get("display")

    return value


# ---------------------------------------------------------------------------
# Issue shaping
# ---------------------------------------------------------------------------

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
_ISSUE_LIST_EXCLUDE: set[str] = {
    "description",
    "followers",
    "self",
    "createdBy",
    "updatedBy",
    "createdAt",
    "updatedAt",
}


def compact_issue(issue: dict[str, Any], *, for_list: bool = False) -> dict[str, Any]:
    """Return a compacted copy of an issue dict.

    * Drops fields not in ``ISSUE_KEEP_FIELDS``
    * Flattens nested objects (users → display name, queue/parent → key)
    * When *for_list* is True, additionally strips verbose fields
      (description, followers, timestamps, etc.) for concise listings.
    """
    fields = ISSUE_KEEP_FIELDS - _ISSUE_LIST_EXCLUDE if for_list else ISSUE_KEEP_FIELDS
    result: dict[str, Any] = {}
    for key in fields:
        if key not in issue:
            continue
        result[key] = _flatten_value(key, issue[key])
    return result


# ---------------------------------------------------------------------------
# Comment shaping
# ---------------------------------------------------------------------------

_COMMENT_KEEP_FIELDS: set[str] = {
    "id",
    "text",
    "createdBy",
    "createdAt",
    "updatedAt",
    "summonees",
    "type",
    "transport",
}

_COMMENT_LIST_EXCLUDE: set[str] = {
    "updatedAt",
    "transport",
}


def compact_comment(comment: dict[str, Any], *, for_list: bool = False) -> dict[str, Any]:
    """Return a compacted copy of a comment dict.

    Keeps text, author, timestamp, and mentioned users.
    """
    fields = _COMMENT_KEEP_FIELDS - _COMMENT_LIST_EXCLUDE if for_list else _COMMENT_KEEP_FIELDS
    result: dict[str, Any] = {}
    for key in fields:
        if key not in comment:
            continue
        result[key] = _flatten_value(key, comment[key])
    return result


# ---------------------------------------------------------------------------
# Domain/action → shaper routing
# ---------------------------------------------------------------------------

# Actions on issue sub-resources that should NOT use the issue shaper.
_COMMENT_ACTIONS: set[str] = {"get_comments", "add_comment", "update_comment"}

# Actions that have no meaningful shaping (return as-is).
_PASSTHROUGH_ACTIONS: set[str] = {
    "get_transitions",
    "execute_transition",
    "get_attachments",
    "get_checklist",
    "get_links",
    "get_worklogs",
    "add_worklog",
    "update_worklog",
    "delete_worklog",
    "delete_comment",
}

_ISSUE_DOMAINS: set[str] = {"issue", "issues"}


def _compact_issue_for_list(issue: dict[str, Any]) -> dict[str, Any]:
    return compact_issue(issue, for_list=True)


def _compact_comment_for_list(comment: dict[str, Any]) -> dict[str, Any]:
    return compact_comment(comment, for_list=True)


def get_shaper(domain: str, action: str = "", *, for_list: bool = False) -> Shaper | None:
    """Return a shaping function for the given operation, or None."""
    if domain not in _ISSUE_DOMAINS:
        return None

    if action in _PASSTHROUGH_ACTIONS:
        return None

    if action in _COMMENT_ACTIONS:
        return _compact_comment_for_list if for_list else compact_comment

    # Default: issue shaper (for issue get/create/update/find)
    return _compact_issue_for_list if for_list else compact_issue
