import base64

import pytest

from api.shared.cursor import Cursor, decode, encode, position_of
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
