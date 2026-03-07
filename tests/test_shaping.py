"""Tests for the shaping module (compact issue representation)."""

from yandex_tracker_mcp.shaping import compact_issue, get_shaper


class TestCompactIssue:
    """Tests for compact_issue field filtering and flattening."""

    def test_keeps_only_allowed_fields(self) -> None:
        issue = {
            "key": "PROJ-1",
            "summary": "Test",
            "votes": 5,
            "favorite": True,
            "commentWithExternalMessageCount": 0,
        }
        result = compact_issue(issue)
        assert set(result.keys()) == {"key", "summary"}

    def test_flattens_status_to_display(self) -> None:
        issue = {
            "key": "X-1",
            "status": {"id": "1", "key": "open", "display": "Open", "self": "..."},
        }
        result = compact_issue(issue)
        assert result["status"] == "Open"

    def test_flattens_type_to_display(self) -> None:
        issue = {
            "key": "X-1",
            "type": {"id": "2", "key": "bug", "display": "Bug", "self": "..."},
        }
        result = compact_issue(issue)
        assert result["type"] == "Bug"

    def test_flattens_priority_to_display(self) -> None:
        issue = {
            "key": "X-1",
            "priority": {"id": "3", "key": "critical", "display": "Critical", "self": "..."},
        }
        result = compact_issue(issue)
        assert result["priority"] == "Critical"

    def test_flattens_assignee_to_display(self) -> None:
        issue = {
            "key": "X-1",
            "assignee": {
                "id": "u1",
                "display": "John Doe",
                "cloudUid": "abc",
                "passportUid": "123",
                "self": "...",
            },
        }
        result = compact_issue(issue)
        assert result["assignee"] == "John Doe"

    def test_flattens_queue_to_key(self) -> None:
        issue = {
            "key": "X-1",
            "queue": {"id": "q1", "key": "PROJ", "display": "Project", "self": "..."},
        }
        result = compact_issue(issue)
        assert result["queue"] == "PROJ"

    def test_flattens_parent_to_key(self) -> None:
        issue = {
            "key": "X-2",
            "parent": {"id": "p1", "key": "X-1", "display": "Parent issue", "self": "..."},
        }
        result = compact_issue(issue)
        assert result["parent"] == "X-1"

    def test_flattens_followers_to_display_names(self) -> None:
        issue = {
            "key": "X-1",
            "followers": [
                {"id": "u1", "display": "Alice", "self": "..."},
                {"id": "u2", "display": "Bob", "self": "..."},
            ],
        }
        result = compact_issue(issue)
        assert result["followers"] == ["Alice", "Bob"]

    def test_preserves_scalar_fields(self) -> None:
        issue = {
            "key": "X-1",
            "summary": "Do stuff",
            "description": "Details here",
            "createdAt": "2025-01-01T00:00:00.000+0000",
            "updatedAt": "2025-01-02T00:00:00.000+0000",
            "deadline": "2025-03-01",
            "start": "2025-01-15",
            "storyPoints": 5.0,
            "self": "https://api.tracker.yandex.net/v3/issues/X-1",
        }
        result = compact_issue(issue)
        assert result["key"] == "X-1"
        assert result["summary"] == "Do stuff"
        assert result["description"] == "Details here"
        assert result["createdAt"] == "2025-01-01T00:00:00.000+0000"
        assert result["deadline"] == "2025-03-01"
        assert result["start"] == "2025-01-15"
        assert result["storyPoints"] == 5.0

    def test_missing_optional_fields_omitted(self) -> None:
        issue = {"key": "X-1", "summary": "Minimal"}
        result = compact_issue(issue)
        assert "deadline" not in result
        assert "parent" not in result
        assert "resolution" not in result

    def test_flattens_createdby_and_updatedby(self) -> None:
        issue = {
            "key": "X-1",
            "createdBy": {"id": "u1", "display": "Alice", "self": "..."},
            "updatedBy": {"id": "u2", "display": "Bob", "self": "..."},
        }
        result = compact_issue(issue)
        assert result["createdBy"] == "Alice"
        assert result["updatedBy"] == "Bob"

    def test_tags_and_components_passed_through(self) -> None:
        issue = {
            "key": "X-1",
            "tags": ["backend", "urgent"],
            "components": [{"id": "1", "display": "API", "self": "..."}],
        }
        result = compact_issue(issue)
        assert result["tags"] == ["backend", "urgent"]


class TestGetShaper:
    """Tests for get_shaper domain routing."""

    def test_returns_shaper_for_issue_domain(self) -> None:
        assert get_shaper("issue") is not None

    def test_returns_shaper_for_issues_domain(self) -> None:
        assert get_shaper("issues") is not None

    def test_returns_none_for_other_domains(self) -> None:
        assert get_shaper("queue") is None
        assert get_shaper("user") is None
        assert get_shaper("board") is None
