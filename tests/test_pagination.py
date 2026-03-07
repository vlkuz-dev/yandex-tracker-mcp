from yandex_tracker_mcp.pagination import _to_int, _to_optional_str, normalize_page

# --- normalize_page: list shape ---


def test_normalize_page_from_array() -> None:
    payload = [{"id": 1}]
    result = normalize_page(payload)
    data = result.to_dict()

    assert data["count"] == 1
    assert data["results"] == [{"id": 1}]
    assert data["next"] is None
    assert data["prev"] is None


# --- normalize_page: results shape ---


def test_normalize_page_from_results_shape() -> None:
    payload = {
        "results": [{"id": 1}, {"id": 2}],
        "count": 10,
        "next": "cursor2",
        "previous": "cursor0",
    }
    result = normalize_page(payload)
    data = result.to_dict()

    assert data["count"] == 10
    assert len(data["results"]) == 2
    assert data["next"] == "cursor2"
    assert data["prev"] == "cursor0"


def test_normalize_page_results_uses_prev_key() -> None:
    payload = {
        "results": [{"id": 1}],
        "prev": "cursor0",
    }
    result = normalize_page(payload)
    assert result.prev == "cursor0"


def test_normalize_page_results_defaults_count_to_len() -> None:
    payload = {"results": [{"a": 1}, {"a": 2}, {"a": 3}]}
    result = normalize_page(payload)
    assert result.count == 3


# --- normalize_page: values/total shape ---


def test_normalize_page_from_values_shape() -> None:
    payload = {
        "values": [{"key": "TASK-1"}, {"key": "TASK-2"}],
        "total": 50,
        "next": "page2",
        "prev": "page0",
    }
    result = normalize_page(payload)
    data = result.to_dict()

    assert data["count"] == 50
    assert len(data["results"]) == 2
    assert data["next"] == "page2"
    assert data["prev"] == "page0"


def test_normalize_page_values_defaults_count_to_len() -> None:
    payload = {"values": [{"k": 1}]}
    result = normalize_page(payload)
    assert result.count == 1
    assert result.next is None
    assert result.prev is None


# --- normalize_page: unrecognized payload ---


def test_normalize_page_unrecognized_dict() -> None:
    payload = {"foo": "bar", "baz": 123}
    result = normalize_page(payload)
    data = result.to_dict()

    assert data["results"] == []
    assert data["count"] == 0
    assert data["next"] is None
    assert data["prev"] is None
    assert data["raw"] == payload


def test_normalize_page_non_list_non_dict() -> None:
    result = normalize_page("unexpected")
    assert result.results == []
    assert result.count == 0


# --- _to_int ---


def test_to_int_with_int() -> None:
    assert _to_int(42, default=0) == 42


def test_to_int_with_digit_string() -> None:
    assert _to_int("123", default=0) == 123


def test_to_int_with_non_digit_string() -> None:
    assert _to_int("abc", default=99) == 99


def test_to_int_with_none() -> None:
    assert _to_int(None, default=7) == 7


def test_to_int_with_float() -> None:
    assert _to_int(3.14, default=0) == 0


# --- _to_optional_str ---


def test_to_optional_str_none() -> None:
    assert _to_optional_str(None) is None


def test_to_optional_str_empty() -> None:
    assert _to_optional_str("") is None


def test_to_optional_str_whitespace() -> None:
    assert _to_optional_str("   ") is None


def test_to_optional_str_valid() -> None:
    assert _to_optional_str("cursor42") == "cursor42"


def test_to_optional_str_strips_whitespace() -> None:
    assert _to_optional_str("  hello  ") == "hello"


def test_to_optional_str_non_string() -> None:
    assert _to_optional_str(42) == "42"
