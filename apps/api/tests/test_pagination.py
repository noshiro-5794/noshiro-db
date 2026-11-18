import pytest
from starlette.requests import Request

from api.shared.cursor import Cursor
from api.shared.pagination import (
    LAST_PAGE,
    cursor_payload,
    ensure_page,
    page_offset,
    page_params,
    page_payload,
)
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
    assert page_params(request("page_size=1000")) == (1, 64)
    assert page_params(request("page_size=0")) == (1, 16)


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
    assert payload["previous"] == "/api/v1/index/entities/?page_size=5&query=x"


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


def test_cursor_links_preserve_repeated_and_blank_filters_with_legacy_query_order():
    payload = cursor_payload(
        request("z=first&z=second&cursor=old&a=&page_size=2"),
        results=[],
        next_cursor=Cursor(offset=2),
        previous_cursor=None,
    )
    assert payload["next"] == "/api/v1/index/entities/?a=&cursor=bz0y&page_size=2&z=first&z=second"
    assert payload["previous"] is None


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "invalid", "LAST"])
def test_invalid_page_numbers_return_404(value):
    with pytest.raises(ProblemError) as caught:
        page_params(request("page=" + value))
    assert caught.value.status_code == 404 and caught.value.detail == "Invalid page."


@pytest.mark.parametrize("value", ["", "0", "-1", "1.5", "invalid"])
def test_invalid_sizes_fall_back_to_the_endpoint_default(value):
    assert page_params(request("page_size=" + value)) == (1, 16)
    assert page_params(request("page_size=" + value), default=64) == (1, 64)


def test_last_page_uses_the_filtered_count_for_both_window_and_links():
    page, size = page_params(request("page=last&page_size=5"))
    assert page == LAST_PAGE and size == 5
    assert page_offset(page, size, 12) == 10
    assert page_offset(page, size, 0) == 0
    ensure_page(page, size, 12)
    assert page_payload(
        request("page=last&page_size=5"), count=12, results=[], page=page, page_size=size
    ) == {
        "count": 12,
        "next": None,
        "previous": "/api/v1/index/entities/?page=2&page_size=5",
        "results": [],
    }


def test_page_links_keep_original_sizes_and_do_not_add_an_omitted_size():
    payload = page_payload(request(), count=100, results=[], page=1, page_size=16)
    assert payload["next"] == "/api/v1/index/entities/?page=2"
    payload = page_payload(request("page_size=1000"), count=100, results=[], page=1, page_size=64)
    assert payload["next"] == "/api/v1/index/entities/?page=2&page_size=1000"
