from api.contexts.access.api.settings import _validate


def test_empty_body_reports_nothing_to_update() -> None:
    values, errors = _validate({})

    assert values == {}
    assert errors == {"non_field_errors": ["No fields to update."]}


def test_unknown_fields_are_not_an_update() -> None:
    _, errors = _validate({"nickname": "someone"})

    assert errors == {"non_field_errors": ["No fields to update."]}


def test_language_uses_the_django_choices() -> None:
    _, errors = _validate({"language": "fr"})
    assert errors == {"language": ['"fr" is not a valid choice.']}

    values, errors = _validate({"language": "ja-JP"})
    assert values == {"language": "ja-JP"}
    assert errors == {}


def test_appearance_uses_the_django_choices() -> None:
    _, errors = _validate({"appearance": "sepia"})

    assert errors == {"appearance": ['"sepia" is not a valid choice.']}


def test_theme_color_must_be_hex_but_may_be_blank() -> None:
    _, errors = _validate({"theme_color": "#12345"})
    assert errors == {"theme_color": ["theme_color must be a hex color, e.g. #66ccff."]}

    values, errors = _validate({"theme_color": ""})
    assert values == {"theme_color": "#7F6FB0"}
    assert errors == {}


def test_adult_content_requires_explicit_confirmation() -> None:
    _, errors = _validate({"show_adult_content": True})

    assert errors == {
        "confirm_adult_content": ["Explicit confirmation is required to enable adult content."]
    }


def test_confirmation_is_not_part_of_the_update() -> None:
    values, errors = _validate({"show_adult_content": True, "confirm_adult_content": True})

    assert values == {"show_adult_content": True}
    assert errors == {}


def test_field_errors_win_over_the_confirmation_check() -> None:
    _, errors = _validate({"language": "fr", "show_adult_content": True})

    assert errors == {"language": ['"fr" is not a valid choice.']}


def test_booleans_accept_the_spellings_drf_accepts() -> None:
    values, errors = _validate({"show_adult_content": "FALSE"})
    assert values == {"show_adult_content": False}
    assert errors == {}

    values, errors = _validate({"show_adult_content": "TRUE", "confirm_adult_content": "on"})
    assert values == {"show_adult_content": True}
    assert errors == {}


def test_invalid_booleans_match_drf() -> None:
    _, errors = _validate({"show_adult_content": "maybe"})

    assert errors == {"show_adult_content": ["Must be a valid boolean."]}
