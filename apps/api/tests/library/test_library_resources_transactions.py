from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import Request
from sqlalchemy import text

from api.contexts.access.dependencies import current_user, optional_user
from api.db import fetch, get_session
from api.main import create_app
from api.shared.problems import ProblemError


@pytest.fixture
async def library_client(integration_session):
    session = integration_session
    users = await fetch(
        session,
        'INSERT INTO "user" (password,is_superuser,first_name,last_name,is_staff,is_active,'
        "date_joined,email,is_email_verified,created_at) "
        "SELECT '',false,'','',false,true,now(),email,true,now() "
        "FROM unnest(ARRAY['library-owner@example.test','library-viewer@example.test',"
        "'library-other@example.test']) AS email RETURNING id",
        {},
    )
    owner, viewer_id, other = [row.id for row in users]
    entries = []
    entities = []
    for index, work_type in enumerate(["anime", "novel", "galgame", "anime"]):
        entity_id = uuid4()
        entities.append(entity_id)
        await fetch(
            session,
            "INSERT INTO entity(id,kind,lifecycle,visibility,audience,spoiler_level,"
            "created_at,updated_at) "
            "VALUES (:id,'work','active','public','general',0,now(),now()) RETURNING id",
            {"id": entity_id},
        )
        await fetch(
            session,
            "INSERT INTO work(entity_id,work_type,popularity,created_at,updated_at) "
            "VALUES (:id,:kind,0,now(),now()) RETURNING entity_id",
            {"id": entity_id, "kind": work_type},
        )
        row = (
            await fetch(
                session,
                "INSERT INTO user_library_entry(user_id,entity_id,status,simple_rating,"
                "rating,comment,"
                "watch_start_date,is_public,created_at,updated_at) "
                "VALUES (:user,:entity,'doing',:simple,:rating,:comment,:start,:public,"
                "now(),now()) "
                "RETURNING id",
                {
                    "user": other if index == 3 else owner,
                    "entity": entity_id,
                    "simple": index + 1,
                    "rating": index + 1,
                    "comment": "100%_literal" if index == 0 else "plain",
                    "start": date(2026, 1, index + 1),
                    "public": index != 2,
                },
            )
        )[0]
        entries.append(row.id)
    collection = (
        await fetch(
            session,
            "INSERT INTO user_collection(user_id,name,note,is_public) "
            "VALUES (:owner,'Public collection','searchable note',true) RETURNING id",
            {"owner": owner},
        )
    )[0].id
    private_collection = (
        await fetch(
            session,
            "INSERT INTO user_collection(user_id,name,note,is_public) "
            "VALUES (:owner,'Private collection','',false) RETURNING id",
            {"owner": owner},
        )
    )[0].id
    for index, entry in enumerate(entries[:3]):
        await fetch(
            session,
            'INSERT INTO user_collection_item(collection_id,user_subject_id,"order",relation) '
            "VALUES (:collection,:entry,:order,'') RETURNING id",
            {"collection": collection, "entry": entry, "order": index},
        )
    await session.commit()

    async def database():
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

    async def viewer(request: Request):
        identifier = request.headers.get("x-test-user")
        return (
            SimpleNamespace(id=int(identifier), is_staff=int(identifier) == owner)
            if identifier
            else None
        )

    async def authenticated(request: Request):
        user = await viewer(request)
        if user is None:
            raise ProblemError(
                status_code=401, detail="Authentication credentials were not provided."
            )
        return user

    app = create_app()
    app.dependency_overrides[get_session] = database
    app.dependency_overrides[current_user] = authenticated
    app.dependency_overrides[optional_user] = viewer
    resources = SimpleNamespace(
        owner=owner,
        viewer=viewer_id,
        other=other,
        entries=entries,
        entities=entities,
        collection=collection,
        private=private_collection,
        app=app,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        headers={"x-test-user": str(owner)},
    ) as client:
        yield session, client, resources


async def add_review(client, entry, **values):
    response = await client.post(
        f"/api/v1/users/me/library/entries/{entry}/reviews/",
        json={"title": "  100%_review  ", "content": "Body", **values},
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_review_create_read_patch_filter_and_page_contract(library_client):
    _, client, data = library_client
    created = await add_review(client, data.entries[0], is_public="false", is_spoiler="true")
    assert created["title"] == "100%_review" and created["is_public"] is False
    assert created["is_spoiler"] is True
    identifier = created["id"]
    path = f"/api/v1/users/me/reviews/{identifier}/"
    assert (await client.get(path)).json() == created
    patched = await client.patch(path, json={"title": " Revised ", "is_public": True})
    assert patched.status_code == 200 and patched.json()["title"] == "Revised"
    assert patched.json()["content"] == "Body" and patched.json()["is_spoiler"] is True
    await add_review(client, data.entries[0], title="100%_only")
    await add_review(client, data.entries[0], title="ordinary")
    literal = await client.get("/api/v1/users/me/reviews/?keyword=%25_")
    assert literal.status_code == 200 and literal.json()["count"] == 1
    assert literal.json()["results"][0]["title"] == "100%_only"
    final = await client.get("/api/v1/users/me/reviews/?ordering=id&page=last&page_size=2")
    assert final.status_code == 200 and final.json()["count"] == 3
    assert final.json()["results"][0]["title"] == "ordinary" and final.json()["next"] is None
    client.headers["x-test-user"] = str(data.other)
    for method in ["get", "patch", "delete"]:
        kwargs = {"json": {"title": "intrusion"}} if method == "patch" else {}
        response = await getattr(client, method)(path, **kwargs)
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_public_reviews_require_public_entry_and_review(library_client):
    session, client, data = library_client
    public = await add_review(client, data.entries[0])
    await add_review(client, data.entries[0], is_public=False)
    await add_review(client, data.entries[2])
    await fetch(
        session,
        "INSERT INTO community_reaction(user_id,review_id,reaction_type,created_at) "
        "VALUES (:viewer,:review,'like',now()) RETURNING id",
        {"viewer": data.viewer, "review": public["id"]},
    )
    client.headers["x-test-user"] = str(data.viewer)
    detail = await client.get(f"/api/v1/users/reviews/{public['id']}/")
    assert detail.status_code == 200 and detail.json()["reaction_count"] == 1
    assert detail.json()["viewer_state"]["has_liked"] is True
    for path in [
        f"/api/v1/users/{data.owner}/reviews/",
        f"/api/v1/users/entities/{data.entities[0]}/reviews/",
    ]:
        response = await client.get(path)
        assert response.status_code == 200 and response.json()["count"] == 1
    filtered = await client.get(f"/api/v1/users/{data.owner}/reviews/?query=absent")
    assert filtered.json()["count"] == 0
    missing = await client.get(f"/api/v1/users/entities/{uuid4()}/reviews/")
    assert missing.status_code == 404
    client.headers.clear()
    anonymous = await client.get(f"/api/v1/users/reviews/{public['id']}/")
    assert anonymous.status_code == 200
    assert anonymous.json()["viewer_state"]["has_liked"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("direction", ["outgoing", "incoming"])
async def test_block_relationship_hides_all_public_owner_resources(library_client, direction):
    session, client, data = library_client
    review = await add_review(client, data.entries[0])
    source, target = (
        (data.viewer, data.owner) if direction == "outgoing" else (data.owner, data.viewer)
    )
    await fetch(
        session,
        "INSERT INTO community_user_block(user_id,blocked_user_id,reason,created_at) "
        "VALUES (:source,:target,'',now()) RETURNING id",
        {"source": source, "target": target},
    )
    await session.commit()
    client.headers["x-test-user"] = str(data.viewer)
    for suffix in [
        "",
        "reviews/",
        "library/entries/",
        "collections/",
        f"collections/{data.collection}/",
        f"collections/{data.collection}/items/",
    ]:
        response = await client.get(f"/api/v1/users/{data.owner}/{suffix}")
        assert response.status_code == 404, (suffix, response.text)
    assert (await client.get(f"/api/v1/users/reviews/{review['id']}/")).status_code == 404
    entity_reviews = await client.get(f"/api/v1/users/entities/{data.entities[0]}/reviews/")
    assert entity_reviews.status_code == 200 and entity_reviews.json()["count"] == 0


@pytest.mark.asyncio
async def test_public_library_and_collection_items_hide_private_entries(library_client):
    _, client, data = library_client
    client.headers.clear()
    library = await client.get(f"/api/v1/users/{data.owner}/library/entries/?ordering=-rating")
    assert library.status_code == 200, library.text
    assert [row["id"] for row in library.json()["results"]] == [data.entries[1], data.entries[0]]
    assert library.json()["results"][1]["watch_start_date"] == "2026-01-01"
    for query in ["subject_type=novel", "keyword=%25_"]:
        result = await client.get(f"/api/v1/users/{data.owner}/library/entries/?{query}")
        assert result.status_code == 200 and result.json()["count"] == 1
    collection = await client.get(f"/api/v1/users/{data.owner}/collections/{data.collection}/")
    assert collection.status_code == 200 and collection.json()["item_count"] == 3
    items = await client.get(f"/api/v1/users/{data.owner}/collections/{data.collection}/items/")
    assert items.status_code == 200 and items.json()["count"] == 2
    assert [item["library_entry_id"] for item in items.json()["results"]] == data.entries[:2]
    note_search = await client.get(f"/api/v1/users/{data.owner}/collections/?keyword=searchable")
    assert note_search.json()["count"] == 1
    for owner, collection_id in [(data.owner, data.private), (data.other, data.collection)]:
        for suffix in ["", "items/"]:
            response = await client.get(
                f"/api/v1/users/{owner}/collections/{collection_id}/{suffix}"
            )
            assert response.status_code == 404
    for suffix in ["collections/", "library/entries/", "reviews/"]:
        assert (await client.get(f"/api/v1/users/9223372036854775807/{suffix}")).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "values,field,message",
    [
        ({"title": None}, "title", "This field may not be null."),
        ({"title": " "}, "title", "This field may not be blank."),
        ({"content": " "}, "content", "UserReview content can not be blank."),
        ({"is_public": None}, "is_public", "This field may not be null."),
        ({"is_spoiler": "invalid"}, "is_spoiler", "Must be a valid boolean."),
        ({"unknown": True}, "non_field_errors", "No fields to update."),
    ],
)
async def test_patch_validation_preserves_field_messages(library_client, values, field, message):
    _, client, data = library_client
    review = await add_review(client, data.entries[0])
    response = await client.patch(f"/api/v1/users/me/reviews/{review['id']}/", json=values)
    assert response.status_code == 400, response.text
    assert response.json()["errors"] == {field: [message]}


@pytest.mark.asyncio
async def test_delete_review_cascades_content_and_keeps_unrelated_data(library_client):
    session, client, data = library_client
    review = await add_review(client, data.entries[0])
    retained = await add_review(client, data.entries[1])
    comment = (
        await fetch(
            session,
            "INSERT INTO community_comment(author_id,review_id,content,visibility,is_spoiler,"
            "is_hidden,is_locked,reply_count,reaction_count,metadata,created_at,updated_at) "
            "VALUES (:user,:review,'reply','public',false,false,false,0,0,'{}',now(),now())"
            " RETURNING id",
            {"user": data.viewer, "review": review["id"]},
        )
    )[0].id
    report = (
        await fetch(
            session,
            "INSERT INTO community_report(reporter_id,comment_id,reason,description,status,"
            "created_at) "
            "VALUES (:user,:comment,'spam','','pending',now()) RETURNING id",
            {"user": data.viewer, "comment": comment},
        )
    )[0].id
    action = (
        await fetch(
            session,
            "INSERT INTO community_moderation_action(moderator_id,report_id,action_type,"
            "reason,metadata,created_at) "
            "VALUES (:user,:report,'hide','','{}',now()) RETURNING id",
            {"user": data.owner, "report": report},
        )
    )[0].id
    await fetch(
        session,
        "INSERT INTO community_notification(recipient_id,comment_id,notification_type,metadata,"
        "created_at) "
        "VALUES (:user,:comment,'commented','{}',now()) RETURNING id",
        {"user": data.owner, "comment": comment},
    )
    response = await client.delete(f"/api/v1/users/me/reviews/{review['id']}/")
    assert response.status_code == 204, response.text
    await session.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert (await fetch(session, "SELECT count(*) AS n FROM community_comment", {}))[0].n == 0
    assert (await fetch(session, "SELECT count(*) AS n FROM community_notification", {}))[0].n == 0
    assert (
        await fetch(
            session,
            "SELECT report_id FROM community_moderation_action WHERE id=:id",
            {"id": action},
        )
    )[0].report_id is None
    remaining = await client.get(f"/api/v1/users/me/reviews/{retained['id']}/")
    assert remaining.status_code == 200 and remaining.json()["id"] == retained["id"]
    assert (await client.get(f"/api/v1/users/me/reviews/{review['id']}/")).status_code == 404
