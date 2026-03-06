from __future__ import annotations

from yandex_tracker_mcp.tools import _normalize_page


def test_normalize_page_from_results_shape() -> None:
    payload = {
        "results": [{"id": 1}, {"id": 2}],
        "count": 10,
        "next": "cursor2",
        "previous": "cursor0",
    }
    result = _normalize_page(payload)
    data = result.to_dict()

    assert data["count"] == 10
    assert len(data["results"]) == 2
    assert data["next"] == "cursor2"
    assert data["prev"] == "cursor0"


def test_normalize_page_from_array() -> None:
    payload = [{"id": 1}]
    result = _normalize_page(payload)
    data = result.to_dict()

    assert data["count"] == 1
    assert data["results"] == [{"id": 1}]
    assert data["next"] is None

