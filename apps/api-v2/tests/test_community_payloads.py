from datetime import UTC, datetime
from types import SimpleNamespace

from api.contexts.community.notifications import notification_payload
from api.contexts.community.people import person
from api.contexts.community.reports import TARGETS, _target


def test_person_is_null_for_a_missing_id() -> None:
    assert person(None, "x", "y") is None


def test_person_defaults_blank_fields() -> None:
    assert person(7, None, None) == {"id": 7, "nickname": "", "avatar": ""}


def test_a_notification_without_a_target_has_null_target() -> None:
    row = SimpleNamespace(
        id=1,
        notification_type="followed",
        metadata={},
        read_at=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        actor_id=2,
        actor_nickname="actor",
        actor_avatar="",
        activity_id=None,
        activity_user_id=None,
        activity_user_nickname=None,
        activity_user_avatar=None,
        activity_target_id=None,
        activity_target_nickname=None,
        activity_target_avatar=None,
    )
    payload = notification_payload(row)
    assert payload["target"] is None
    assert payload["is_read"] is False
    assert payload["read_at"] is None
    assert payload["created_at"] == "2026-01-01T00:00:00Z"


def test_an_activity_target_carries_both_people() -> None:
    row = SimpleNamespace(
        id=1,
        notification_type="followed",
        metadata={"actor_id": 2},
        read_at=datetime(2026, 1, 2, tzinfo=UTC),
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        actor_id=2,
        actor_nickname="actor",
        actor_avatar="",
        activity_id=9,
        activity_user_id=2,
        activity_user_nickname="actor",
        activity_user_avatar="",
        activity_target_id=3,
        activity_target_nickname="target",
        activity_target_avatar="a.png",
    )
    payload = notification_payload(row)
    assert payload["is_read"] is True
    assert payload["target"]["type"] == "activity"
    assert payload["target"]["user"]["id"] == 2
    assert payload["target"]["target_user"] == {
        "id": 3,
        "nickname": "target",
        "avatar": "a.png",
    }


def test_the_report_target_names_the_one_foreign_key_set() -> None:
    report = SimpleNamespace(**{f"{kind}_id": None for kind in TARGETS})
    assert _target(report) is None
    report.collection_id = 5
    assert _target(report) == {"type": "collection", "id": 5}


def test_a_post_target_names_its_author() -> None:
    from types import SimpleNamespace

    from api.contexts.community.targets import post_target

    row = SimpleNamespace(post_id=None)
    assert post_target(row) is None
    row = SimpleNamespace(post_id=5, post_author_id=7, post_nickname="a", post_avatar="")
    assert post_target(row) == {
        "type": "post",
        "id": 5,
        "author": {"id": 7, "nickname": "a", "avatar": ""},
    }


def test_first_target_prefers_the_post() -> None:
    from types import SimpleNamespace

    from api.contexts.community.targets import first_target

    row = SimpleNamespace(
        post_id=5,
        post_author_id=7,
        post_nickname="a",
        post_avatar="",
        comment_id=None,
        review_id=None,
        collection_id=None,
        activity_id=None,
        activity_user_id=None,
        activity_user_nickname=None,
        activity_user_avatar=None,
        activity_target_id=None,
        activity_target_nickname=None,
        activity_target_avatar=None,
    )
    assert first_target(row)["type"] == "post"


def test_first_target_falls_back_to_nothing() -> None:
    from types import SimpleNamespace

    from api.contexts.community.targets import first_target

    row = SimpleNamespace(
        post_id=None,
        comment_id=None,
        review_id=None,
        collection_id=None,
        activity_id=None,
    )
    assert first_target(row) is None
