from types import SimpleNamespace

import pytest

from api.contexts.community import notification_targets


def notification(identifier, **targets):
    return SimpleNamespace(
        id=identifier,
        **{f"{kind}_id": targets.get(kind) for kind in notification_targets.TARGET_FIELDS},
    )


@pytest.mark.asyncio
async def test_batch_targets_include_nested_activity_comment_and_content_owners(monkeypatch):
    owner = {"user_id": 1, "nickname": "Author", "avatar": ""}
    rows = {
        "post": [SimpleNamespace(id=10, **owner)],
        "review": [SimpleNamespace(id=20, **owner)],
        "collection": [SimpleNamespace(id=30, **owner)],
        "activity": [
            SimpleNamespace(
                id=40,
                **owner,
                target_user_id=2,
                target_nickname="Target",
                target_avatar="",
                entity_id="entity",
                post_id=10,
                review_id=20,
                collection_id=30,
                comment_id=50,
            )
        ],
        "comment": [
            SimpleNamespace(
                id=50,
                **owner,
                parent_id=49,
                post_id=10,
                review_id=None,
                collection_id=None,
                activity_id=None,
            )
        ],
    }
    requested = []

    async def query(session, sql, params):
        kind = next(
            kind for kind, prefix in notification_targets.QUERIES.items() if sql.startswith(prefix)
        )
        requested.append(kind)
        return [row for row in rows[kind] if row.id in params["ids"]]

    monkeypatch.setattr(notification_targets, "fetch", query)
    result = await notification_targets.load(
        object(),
        [
            notification(1, activity=40),
            notification(2, post=10),
            notification(3, review=20),
            notification(4, collection=30),
            notification(5, comment=50),
            notification(6),
        ],
    )
    assert result[1]["post"] == result[2]
    assert result[1]["review"] == result[3]
    assert result[1]["collection"] == result[4]
    assert result[1]["comment"] == result[5]
    assert result[1]["entity"] == {"id": "entity"}
    assert result[5]["parent_id"] == 49
    assert result[2]["author"] == {"id": 1, "nickname": "Author", "avatar": ""}
    assert result[6] is None
    assert len(requested) == 5


@pytest.mark.asyncio
async def test_recursive_target_cycle_is_finite_and_missing_reference_is_null(monkeypatch):
    async def query(session, sql, params):
        if "FROM community_activity item" in sql:
            return [
                SimpleNamespace(
                    id=1,
                    user_id=1,
                    nickname="",
                    avatar="",
                    target_user_id=None,
                    target_nickname=None,
                    target_avatar=None,
                    entity_id=None,
                    comment_id=2,
                )
            ]
        if "FROM community_comment item" in sql:
            return [
                SimpleNamespace(
                    id=2, user_id=1, nickname="", avatar="", parent_id=None, activity_id=1
                )
            ]
        return []

    monkeypatch.setattr(notification_targets, "fetch", query)
    result = await notification_targets.load(
        object(), [notification(1, activity=1), notification(2, post=404)]
    )
    assert result[1]["comment"]["activity"] == {"type": "activity", "id": 1}
    assert result[2] is None
