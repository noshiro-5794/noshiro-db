import asyncio
import os
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.contexts.access.dependencies import current_user
from api.contexts.community import comments
from api.contexts.presentation.fragments import fetch
from api.db import get_session
from api.main import create_app
from tests.test_library_resources_transactions import add_review
from tests.test_library_resources_transactions import library_client as library_client


@pytest.fixture
async def comment_client(library_client):
    session, client, data = library_client
    post = await client.post(
        "/api/v1/community/posts/",
        json={
            "content": "Owner post",
            "entity_id": str(data.entities[0]),
        },
    )
    assert post.status_code == 201, post.text
    review = await add_review(client, data.entries[0])
    activity = (
        await fetch(
            session,
            "INSERT INTO community_activity(user_id,entity_id,activity_type,message,visibility,"
            "feed_policy,group_key,dedupe_key,metadata,created_at) "
            "VALUES (:owner,:entity,'followed','','public','normal','','','{}',now()) RETURNING id",
            {"owner": data.owner, "entity": data.entities[0]},
        )
    )[0].id
    await session.commit()
    data.targets = {
        "post": post.json()["id"],
        "review": review["id"],
        "collection": data.collection,
        "activity": activity,
    }
    yield session, client, data


async def add_comment(client, kind, identifier, **values):
    return await client.post(
        "/api/v1/community/comments/",
        json={
            "target_type": kind,
            "target_id": identifier,
            "content": "Comment body",
            **values,
        },
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["post", "review", "collection", "activity"])
async def test_comment_targets_create_activity_and_notification_atomically(comment_client, kind):
    session, client, data = comment_client
    client.headers["x-test-user"] = str(data.viewer)
    response = await add_comment(client, kind, data.targets[kind], is_spoiler="false")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["target"] == {"type": kind, "id": data.targets[kind]}
    assert body["is_spoiler"] is False and body["author"]["id"] == data.viewer
    activity = (
        await fetch(
            session, "SELECT * FROM community_activity WHERE comment_id=:id", {"id": body["id"]}
        )
    )[0]
    assert activity.message == f"Commented on a {kind}"
    assert activity.metadata == {"target": body["target"], "comment": {"id": body["id"]}}
    assert activity.entity_id == (None if kind == "collection" else data.entities[0])
    notification = (
        await fetch(
            session, "SELECT * FROM community_notification WHERE comment_id=:id", {"id": body["id"]}
        )
    )[0]
    assert notification.recipient_id == data.owner and notification.actor_id == data.viewer
    assert notification.activity_id == activity.id
    assert notification.metadata == {
        "post_id": data.targets[kind] if kind == "post" else None,
        "review_id": data.targets[kind] if kind == "review" else None,
        "collection_id": data.targets[kind] if kind == "collection" else None,
        "comment_id": body["id"],
    }
    listing = await client.get(
        "/api/v1/community/comments/",
        params={
            "target_type": kind,
            "target_id": data.targets[kind],
        },
    )
    assert listing.status_code == 200 and listing.json()["results"] == [body]


@pytest.mark.asyncio
async def test_nested_post_route_and_reply_recipient_share_the_same_service(comment_client):
    session, client, data = comment_client
    post = data.targets["post"]
    initial = await client.post(
        f"/api/v1/community/posts/{post}/comments/",
        json={
            "content": "Owner comment",
            "parent_id": 0,
        },
    )
    assert initial.status_code == 201, initial.text
    assert initial.json()["parent_id"] is None
    assert (await fetch(session, "SELECT count(*) AS n FROM community_notification", {}))[0].n == 0
    client.headers["x-test-user"] = str(data.viewer)
    parent = await add_comment(client, "post", post)
    assert parent.status_code == 201
    client.headers["x-test-user"] = str(data.other)
    reply = await add_comment(client, "post", post, parent_id=parent.json()["id"])
    assert reply.status_code == 201
    notification = (
        await fetch(
            session,
            "SELECT recipient_id FROM community_notification WHERE comment_id=:id",
            {"id": reply.json()["id"]},
        )
    )[0]
    assert notification.recipient_id == data.viewer
    assert (
        await fetch(session, "SELECT reply_count FROM community_post WHERE id=:id", {"id": post})
    )[0].reply_count == 3
    listing = await client.get(f"/api/v1/community/posts/{post}/comments/")
    assert listing.status_code == 200 and listing.json()["count"] == 3


@pytest.mark.asyncio
async def test_hidden_parent_and_deleted_reply_keep_counts_and_activity_visibility(comment_client):
    session, client, data = comment_client
    post = data.targets["post"]
    parent = (await add_comment(client, "post", post)).json()
    client.headers["x-test-user"] = str(data.viewer)
    reply = (await add_comment(client, "post", post, parent_id=parent["id"])).json()
    client.headers["x-test-user"] = str(data.owner)
    assert (await client.delete(f"/api/v1/community/comments/{parent['id']}/")).status_code == 204
    listing = await client.get(
        "/api/v1/community/comments/",
        params={
            "target_type": "post",
            "target_id": post,
        },
    )
    assert listing.json()["results"][0]["author"] is None
    assert listing.json()["results"][0]["is_hidden"] is True
    assert listing.json()["results"][0]["content"] == ""
    activity = (
        await fetch(
            session,
            "SELECT feed_policy FROM community_activity WHERE comment_id=:id",
            {"id": parent["id"]},
        )
    )[0]
    assert activity.feed_policy == "hidden"
    client.headers["x-test-user"] = str(data.viewer)
    assert (await client.delete(f"/api/v1/community/comments/{reply['id']}/")).status_code == 204
    assert (
        await fetch(
            session, "SELECT reply_count FROM community_comment WHERE id=:id", {"id": parent["id"]}
        )
    )[0].reply_count == 0
    assert (
        await fetch(session, "SELECT reply_count FROM community_post WHERE id=:id", {"id": post})
    )[0].reply_count == 1
    assert (
        await client.get(
            "/api/v1/community/comments/",
            params={
                "target_type": "post",
                "target_id": post,
            },
        )
    ).json()["count"] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("relation", ["mute", "outgoing_block", "incoming_block"])
async def test_comment_listing_filters_muted_and_blocked_authors(comment_client, relation):
    session, client, data = comment_client
    await add_comment(client, "post", data.targets["post"])
    if relation == "mute":
        await fetch(
            session,
            "INSERT INTO community_user_mute(user_id,muted_user_id,reason,created_at) "
            "VALUES (:viewer,:owner,'',now()) RETURNING id",
            {"viewer": data.viewer, "owner": data.owner},
        )
    else:
        source, target = (
            (data.viewer, data.owner) if relation == "outgoing_block" else (data.owner, data.viewer)
        )
        await fetch(
            session,
            "INSERT INTO community_user_block(user_id,blocked_user_id,reason,created_at) "
            "VALUES (:source,:target,'',now()) RETURNING id",
            {"source": source, "target": target},
        )
    await session.commit()
    client.headers["x-test-user"] = str(data.viewer)
    result = await client.get(
        "/api/v1/community/comments/",
        params={
            "target_type": "post",
            "target_id": data.targets["post"],
        },
    )
    assert result.status_code == 200 and result.json()["count"] == 0
    created = await add_comment(client, "post", data.targets["post"])
    assert created.status_code == (201 if relation == "mute" else 403)
    if relation != "mute":
        assert created.json()["code"] == "community.interaction_blocked"


@pytest.mark.asyncio
async def test_locked_targets_parents_and_other_authors_are_protected(comment_client):
    session, client, data = comment_client
    post = data.targets["post"]
    parent = (await add_comment(client, "post", post)).json()
    client.headers["x-test-user"] = str(data.viewer)
    path = f"/api/v1/community/comments/{parent['id']}/"
    for method in ["patch", "delete"]:
        kwargs = {"json": {"content": "Intrusion"}} if method == "patch" else {}
        forbidden = await getattr(client, method)(path, **kwargs)
        assert (
            forbidden.status_code == 403
            and forbidden.json()["code"] == "community.permission_denied"
        )
    await fetch(
        session,
        "UPDATE community_comment SET is_locked=true WHERE id=:id RETURNING id",
        {"id": parent["id"]},
    )
    await session.commit()
    assert (await add_comment(client, "post", post, parent_id=parent["id"])).status_code == 409
    await fetch(
        session, "UPDATE community_post SET is_locked=true WHERE id=:id RETURNING id", {"id": post}
    )
    await session.commit()
    assert (await add_comment(client, "post", post)).status_code == 409


@pytest.mark.asyncio
async def test_activity_targets_inherit_private_related_resource_visibility(comment_client):
    session, client, data = comment_client
    await fetch(
        session,
        "UPDATE community_activity SET user_subject_id=:entry WHERE id=:activity RETURNING id",
        {"entry": data.entries[2], "activity": data.targets["activity"]},
    )
    await session.commit()
    result = await client.get(
        "/api/v1/community/comments/",
        params={
            "target_type": "activity",
            "target_id": data.targets["activity"],
        },
    )
    assert result.status_code == 404 and result.json()["code"] == "community.target_not_found"
    assert (await add_comment(client, "activity", data.targets["activity"])).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "values,field,message",
    [
        ({"content": ""}, "content", "This field may not be blank."),
        ({"content": " "}, "content", "Comment content can not be blank."),
        ({"content": "x" * 5001}, "content", "Ensure this field has no more than 5000 characters."),
        ({"parent_id": None}, "parent_id", "This field may not be null."),
        ({"parent_id": True}, "parent_id", "A valid integer is required."),
        ({"target_id": 0}, "target_id", "Ensure this value is greater than or equal to 1."),
        ({"is_spoiler": "invalid"}, "is_spoiler", "Must be a valid boolean."),
    ],
)
async def test_comment_validation_matches_existing_field_messages(
    comment_client, values, field, message
):
    _, client, data = comment_client
    response = await add_comment(client, "post", data.targets["post"], **values)
    assert response.status_code == 400, response.text
    assert response.json()["errors"] == {field: [message]}


@pytest.mark.asyncio
async def test_notification_failure_rolls_back_comment_activity_and_reply_count(
    comment_client, monkeypatch
):
    session, client, data = comment_client
    client.headers["x-test-user"] = str(data.viewer)
    real_fetch = comments.fetch

    async def fail_notification(session, query, parameters):
        if query.startswith("INSERT INTO community_notification"):
            raise RuntimeError("notification insert failed")
        return await real_fetch(session, query, parameters)

    monkeypatch.setattr(comments, "fetch", fail_notification)
    with pytest.raises(RuntimeError, match="notification insert failed"):
        await add_comment(client, "post", data.targets["post"])
    assert (await fetch(session, "SELECT count(*) AS n FROM community_comment", {}))[0].n == 0
    assert (
        await fetch(
            session, "SELECT count(*) AS n FROM community_activity WHERE comment_id IS NOT NULL", {}
        )
    )[0].n == 0
    assert (
        await fetch(
            session,
            "SELECT reply_count FROM community_post WHERE id=:id",
            {"id": data.targets["post"]},
        )
    )[0].reply_count == 0


@pytest.mark.asyncio
async def test_concurrent_comments_preserve_counts_and_notifications(integration_session):

    # The integration fixture validates the disposable database before committed
    # rows become visible to independent request connections in this case.
    engine = create_async_engine(
        os.environ["NOSHIRO_INTEGRATION_DATABASE_URL"].replace(
            "postgresql://", "postgresql+asyncpg://", 1
        ),
        poolclass=NullPool,
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    users = []
    post_id = None
    try:
        async with factory() as session:
            users = [
                row.id
                for row in await fetch(
                    session,
                    'INSERT INTO "user"(password,is_superuser,first_name,last_name,is_staff,'
                    "is_active,"
                    "date_joined,email,is_email_verified,created_at) "
                    "SELECT '',false,'','',false,true,now(),email,true,now() "
                    "FROM unnest(CAST(:emails AS text[])) AS email RETURNING id",
                    {"emails": [f"comment-{uuid4()}@example.test" for _ in range(2)]},
                )
            ]
            post_id = (
                await fetch(
                    session,
                    "INSERT INTO community_post(author_id,post_type,content,visibility,feed_policy,"
                    "is_spoiler,is_nsfw,is_pinned,is_locked,reply_count,reaction_count,metadata,"
                    "last_activity_at,created_at,updated_at) "
                    "VALUES (:owner,'status','Post','public','normal',false,false,false,false,0,0,"
                    "'{}',now(),now(),now()) RETURNING id",
                    {"owner": users[0]},
                )
            )[0].id
            await session.commit()

        async def database():
            async with factory() as session:
                yield session

        app = create_app()
        app.dependency_overrides[get_session] = database
        app.dependency_overrides[current_user] = lambda: SimpleNamespace(id=users[1])
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            responses = await asyncio.gather(
                *(add_comment(client, "post", post_id) for _ in range(20)),
                return_exceptions=True,
            )
        assert all(
            isinstance(response, httpx.Response) and response.status_code == 201
            for response in responses
        ), responses
        async with factory() as session:
            post = (
                await fetch(
                    session, "SELECT reply_count FROM community_post WHERE id=:id", {"id": post_id}
                )
            )[0]
            assert post.reply_count == 20
            for table in ["community_comment", "community_activity", "community_notification"]:
                rows = await fetch(
                    session, f"SELECT count(*) AS n FROM {table} WHERE post_id=:id", {"id": post_id}
                )
                assert rows[0].n == 20, table
    finally:
        async with engine.begin() as connection:
            if post_id is not None:
                await connection.execute(
                    text("DELETE FROM community_post WHERE id=:id"), {"id": post_id}
                )
            await connection.execute(
                text('DELETE FROM "user" WHERE id=ANY(CAST(:users AS bigint[]))'), {"users": users}
            )
        await engine.dispose()
