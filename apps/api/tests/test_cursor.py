import base64
from datetime import UTC, datetime

import pytest

from api.shared.cursor import Cursor, decode, encode, paginate, position_of, timestamp_position
from api.shared.problems import ProblemError


def test_empty_cursor_is_the_first_page() -> None:
    assert decode(None) == Cursor()


def test_round_trip() -> None:
    cursor = Cursor(offset=16, reverse=True, position="2026-10-25 09:00:00+00:00")
    assert decode(encode(cursor)) == cursor


def test_first_page_cursor_has_no_tokens() -> None:
    assert decode(encode(Cursor())).offset == 0
    assert base64.b64decode(encode(Cursor())).decode() == ""


def test_garbage_is_a_404() -> None:
    with pytest.raises(ProblemError) as error:
        decode("not-base64!")
    assert error.value.status_code == 404


def test_position_is_the_string_of_the_field() -> None:
    class Row:
        created_at = None

    assert position_of(Row()) == "None"
    assert position_of({"created_at": "x"}) == "x"


def test_large_offset_is_capped_like_legacy_cursors():
    assert decode(encode(Cursor(offset=1500))).offset == 1000


def test_tied_first_page_advances_with_an_offset_without_losing_same_timestamp_rows():
    rows = [{"id": index, "created_at": 3} for index in [5, 4, 3]]
    page, next_cursor, previous_cursor = paginate(rows, Cursor(), 2)
    assert [row["id"] for row in page] == [5, 4]
    assert next_cursor == Cursor(offset=2) and previous_cursor is None


def test_tied_boundary_and_direction_change_preserve_legacy_offsets():
    rows = [{"id": 3, "created_at": 3}, {"id": 2, "created_at": 2}, {"id": 1, "created_at": 1}]
    page, next_cursor, previous_cursor = paginate(rows, Cursor(offset=2), 2)
    assert [row["id"] for row in page] == [3, 2]
    assert next_cursor == Cursor(position="2")
    assert previous_cursor == Cursor(offset=1, reverse=True, position="2")
    back, following, previous = paginate(
        [{"id": 4, "created_at": 3}, {"id": 5, "created_at": 3}], previous_cursor, 2
    )
    assert [row["id"] for row in back] == [5, 4]
    assert following == Cursor(offset=2) and previous is None


def test_empty_directional_pages_keep_the_cursor_position():
    assert paginate([], Cursor(position="3"), 2) == ([], None, Cursor(reverse=True, position="3"))
    assert paginate([], Cursor(reverse=True, position="3"), 2) == ([], Cursor(position="3"), None)


def test_timestamp_position_supports_legacy_datetime_strings_and_naive_utc_dates():
    assert timestamp_position("2026-11-18 12:00:00+00:00") == datetime(2026, 11, 18, 12, tzinfo=UTC)
    assert timestamp_position("2026-11-18") == datetime(2026, 11, 18, tzinfo=UTC)


def test_invalid_timestamp_is_rejected_as_an_invalid_cursor():
    with pytest.raises(ProblemError) as caught:
        timestamp_position("invalid-date")
    assert caught.value.status_code == 404 and caught.value.detail == "Invalid cursor."
