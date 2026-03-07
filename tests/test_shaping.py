"""Tests for the shaping module (compact issue/comment representation)."""

from yandex_tracker_mcp.shaping import compact_comment, compact_issue, get_shaper


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


class TestCompactIssueForList:
    """Tests for compact_issue with for_list=True (paginated listings)."""

    def test_excludes_description(self) -> None:
        issue = {"key": "X-1", "summary": "Task", "description": "Long text..."}
        result = compact_issue(issue, for_list=True)
        assert "description" not in result
        assert result["key"] == "X-1"
        assert result["summary"] == "Task"

    def test_excludes_verbose_fields(self) -> None:
        issue = {
            "key": "X-1",
            "summary": "Task",
            "self": "https://...",
            "followers": [{"id": "u1", "display": "Alice", "self": "..."}],
            "createdBy": {"id": "u1", "display": "Alice", "self": "..."},
            "updatedBy": {"id": "u2", "display": "Bob", "self": "..."},
            "createdAt": "2025-01-01T00:00:00.000+0000",
            "updatedAt": "2025-01-02T00:00:00.000+0000",
        }
        result = compact_issue(issue, for_list=True)
        excluded = (
            "description", "followers", "self",
            "createdBy", "updatedBy", "createdAt", "updatedAt",
        )
        for field in excluded:
            assert field not in result, f"{field} should be excluded"

    def test_keeps_essential_fields(self) -> None:
        issue = {
            "key": "X-1",
            "summary": "Task",
            "status": {"id": "1", "key": "open", "display": "Open", "self": "..."},
            "type": {"id": "2", "key": "task", "display": "Task", "self": "..."},
            "priority": {"id": "3", "key": "normal", "display": "Normal", "self": "..."},
            "assignee": {"id": "u1", "display": "Alice", "self": "..."},
            "queue": {"id": "q1", "key": "PROJ", "display": "Project", "self": "..."},
            "deadline": "2025-03-01",
            "tags": ["urgent"],
        }
        result = compact_issue(issue, for_list=True)
        assert result["key"] == "X-1"
        assert result["status"] == "Open"
        assert result["type"] == "Task"
        assert result["priority"] == "Normal"
        assert result["assignee"] == "Alice"
        assert result["queue"] == "PROJ"
        assert result["deadline"] == "2025-03-01"
        assert result["tags"] == ["urgent"]


class TestCompactComment:
    """Tests for compact_comment."""

    def test_keeps_text_and_author(self) -> None:
        comment = {
            "id": 123,
            "text": "Please approve",
            "createdBy": {
                "id": "u1",
                "display": "Alice",
                "cloudUid": "abc",
                "passportUid": 999,
                "self": "...",
            },
            "createdAt": "2025-01-01T00:00:00.000+0000",
            "self": "https://...",
            "longId": "abc123",
            "version": 1,
        }
        result = compact_comment(comment)
        assert result["id"] == 123
        assert result["text"] == "Please approve"
        assert result["createdBy"] == "Alice"
        assert result["createdAt"] == "2025-01-01T00:00:00.000+0000"
        assert "self" not in result
        assert "longId" not in result
        assert "version" not in result

    def test_flattens_summonees(self) -> None:
        comment = {
            "id": 456,
            "text": "@bob please review",
            "summonees": [
                {"id": "u2", "display": "Bob", "self": "..."},
            ],
        }
        result = compact_comment(comment)
        assert result["summonees"] == ["Bob"]

    def test_list_mode_excludes_verbose(self) -> None:
        comment = {
            "id": 789,
            "text": "Done",
            "createdBy": {"id": "u1", "display": "Alice", "self": "..."},
            "createdAt": "2025-01-01T00:00:00.000+0000",
            "updatedAt": "2025-01-02T00:00:00.000+0000",
            "transport": "internal",
            "type": "standard",
        }
        result = compact_comment(comment, for_list=True)
        assert result["text"] == "Done"
        assert result["createdBy"] == "Alice"
        assert "updatedAt" not in result
        assert "transport" not in result
        assert result["type"] == "standard"


class TestGetShaper:
    """Tests for get_shaper domain/action routing."""

    def test_returns_issue_shaper_for_get(self) -> None:
        shaper = get_shaper("issue", "get")
        assert shaper is not None
        result = shaper({"key": "X-1", "description": "text"})
        assert result["description"] == "text"

    def test_returns_issue_list_shaper_for_find(self) -> None:
        shaper = get_shaper("issues", "find", for_list=True)
        assert shaper is not None
        result = shaper({"key": "X-1", "description": "text"})
        assert "description" not in result

    def test_returns_comment_shaper_for_get_comments(self) -> None:
        shaper = get_shaper("issue", "get_comments")
        assert shaper is not None
        result = shaper({"id": 1, "text": "hi", "longId": "abc", "version": 1})
        assert result["text"] == "hi"
        assert "longId" not in result

    def test_returns_comment_list_shaper(self) -> None:
        shaper = get_shaper("issue", "get_comments", for_list=True)
        assert shaper is not None
        comment = {"id": 1, "text": "hi", "transport": "internal"}
        result = shaper(comment)
        assert "transport" not in result

    def test_returns_none_for_passthrough_actions(self) -> None:
        assert get_shaper("issue", "get_transitions") is None
        assert get_shaper("issue", "get_attachments") is None
        assert get_shaper("issue", "get_checklist") is None
        assert get_shaper("issue", "get_links") is None

    def test_returns_none_for_other_domains(self) -> None:
        assert get_shaper("queue", "get_metadata") is None
        assert get_shaper("user", "get") is None
        assert get_shaper("board", "get") is None
