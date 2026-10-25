import pytest
from starlette.requests import Request

from api.shared.pagination import ensure_page, page_params, page_payload
from api.shared.problems import ProblemError


def request(query: str = "") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/index/entities/",
            "query_string": query.encode(),
            "headers": [],
        }
    )


def test_defaults_to_the_first_page() -> None:
    assert page_params(request()) == (1, 16)


def test_reads_both_parameters() -> None:
    assert page_params(request("page=3&page_size=5")) == (3, 5)


def test_clamps_to_the_configured_bounds() -> None:
    assert page_params(request("page=0&page_size=1000")) == (1, 64)
    assert page_params(request("page_size=0")) == (1, 1)


def test_links_keep_the_other_query_parameters() -> None:
    payload = page_payload(
        request("page=2&page_size=5&query=x"),
        count=12,
        results=[],
        page=2,
        page_size=5,
    )
    assert "page=3" in payload["next"]
    assert "query=x" in payload["next"]
    assert "page=1" in payload["previous"]


def test_no_next_on_the_last_page_and_no_previous_on_the_first() -> None:
    last = page_payload(request("page=3"), count=32, results=[], page=3, page_size=16)
    assert last["next"] is None and last["previous"] is not None
    first = page_payload(request(), count=32, results=[], page=1, page_size=16)
    assert first["previous"] is None and first["next"] is not None


def test_a_page_past_the_end_is_a_404() -> None:
    with pytest.raises(ProblemError) as error:
        ensure_page(3, 16, 20)
    assert error.value.status_code == 404
    assert error.value.detail == "Invalid page."
