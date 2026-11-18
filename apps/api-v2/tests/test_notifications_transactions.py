import pytest

from api.contexts.community import notifications
from api.contexts.presentation.fragments import fetch
from api.shared.cursor import Cursor


@pytest.mark.asyncio
async def test_notification_read_filter_selects_both_states_and_read_one_is_idempotent(
    integration_session,
):
    session = integration_session
    user_id = (
        await fetch(
            session,
            'INSERT INTO "user" (password,is_superuser,first_name,last_name,is_staff,is_active,'
            "date_joined,email,is_email_verified,created_at) "
            "VALUES ('',false,'','',false,true,now(),'notification@example.test',true,now()) "
            "RETURNING id",
            {},
        )
    )[0].id
    for read in [True, False]:
        await fetch(
            session,
            "INSERT INTO community_notification "
            "(recipient_id,notification_type,metadata,created_at,read_at) "
            "VALUES (:user,'followed','{}',clock_timestamp(),"
            "CASE WHEN :read THEN now() ELSE NULL END) RETURNING id",
            {"user": user_id, "read": read},
        )
    for state in [True, False, None]:
        page, _ = await notifications.list_for_user(
            session, user_id=user_id, cursor=Cursor(), page_size=16, is_read=state
        )
        assert len(page) == (2 if state is None else 1)
        if state is not None:
            assert all(row["is_read"] == state for row in page)
    unread, _ = await notifications.list_for_user(
        session, user_id=user_id, cursor=Cursor(), page_size=16, is_read=False
    )
    first = await notifications.read_one(session, user_id=user_id, notification_id=unread[0]["id"])
    again = await notifications.read_one(session, user_id=user_id, notification_id=unread[0]["id"])
    assert first == again and first["is_read"] is True
    assert await notifications.unread_count(session, user_id=user_id) == 0
