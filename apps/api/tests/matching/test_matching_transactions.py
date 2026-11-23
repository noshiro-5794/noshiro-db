"""Resolution rollback against an explicitly configured PostgreSQL test database."""

import os
from unittest.mock import AsyncMock
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from api.contexts.index import resolution
from api.db import fetch

DATABASE = os.environ.get("NOSHIRO_INTEGRATION_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not DATABASE, reason="dedicated PostgreSQL integration database required"
)


@pytest.mark.asyncio
async def test_refused_merge_rolls_back_decision_before_safe_fallback(monkeypatch):
    if not urlsplit(DATABASE).path.endswith("_test"):
        pytest.fail("Integration database name must end with _test.")
    engine = create_async_engine(
        DATABASE.replace("postgresql://", "postgresql+asyncpg://", 1), poolclass=NullPool
    )
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(bind=connection) as session:
                    left, right, candidate = uuid4(), uuid4(), uuid4()
                    for entity_id in (left, right):
                        await fetch(
                            session,
                            """
                            INSERT INTO entity (id,kind,lifecycle,visibility,audience,spoiler_level,
                              created_at,updated_at)
                            VALUES (:id,'work','active','public','general',0,now(),now())
                            RETURNING id
                        """,
                            {"id": entity_id},
                        )
                    await fetch(
                        session,
                        """
                        INSERT INTO match_candidate (id,left_entity_id,right_entity_id,score,
                          runner_up_margin,policy_version,status,hard_conflicts,created_at,updated_at)
                        VALUES (:id,:left,:right,1,1,'transaction-fixture','pending','[]',
                          now(),now())
                        RETURNING id
                    """,
                        {"id": candidate, "left": left, "right": right},
                    )
                    monkeypatch.setattr(
                        resolution,
                        "merge",
                        AsyncMock(side_effect=resolution.UserLibraryConflict("fixture conflict")),
                    )
                    with pytest.raises(resolution.UserLibraryConflict):
                        await resolution.decide(
                            session, candidate_id=candidate, outcome="bind", reason="fixture"
                        )
                    rows = await fetch(
                        session,
                        "SELECT status FROM match_candidate WHERE id=:id",
                        {"id": candidate},
                    )
                    assert rows[0].status == "pending"
                    rows = await fetch(
                        session,
                        "SELECT id FROM candidate_decision WHERE candidate_id=:id",
                        {"id": candidate},
                    )
                    assert rows == []
                    await resolution.decide(
                        session, candidate_id=candidate, outcome="abstain", reason="safe fallback"
                    )
                    rows = await fetch(
                        session,
                        "SELECT outcome FROM candidate_decision WHERE candidate_id=:id",
                        {"id": candidate},
                    )
                    assert len(rows) == 1 and rows[0].outcome == "abstain"
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reviewed_group_keeps_two_work_identities(integration_session, register_provider):
    from api.worker.subject_import import import_subject

    session = integration_session
    await register_provider("bangumi", "Bangumi")
    left = await import_subject(session, {"id": 1, "type": 2, "name": "First work"})
    right = await import_subject(session, {"id": 2, "type": 2, "name": "Second work"})
    candidate = uuid4()
    await fetch(
        session,
        """
        INSERT INTO match_candidate (id,left_entity_id,right_entity_id,score,runner_up_margin,
          policy_version,status,hard_conflicts,created_at,updated_at)
        VALUES (:id,:left,:right,1,1,'transaction-fixture','pending','[]',now(),now())
        RETURNING id
        """,
        {"id": candidate, "left": left, "right": right},
    )
    await resolution.decide(session, candidate_id=candidate, outcome="group", reason="Same season")
    edges = await fetch(
        session,
        "SELECT from_entity_id, to_entity_id FROM entity_relation"
        " WHERE relation_type='same-season'",
        {},
    )
    assert {tuple(edge) for edge in edges} == {(left, right), (right, left)}
    assert await resolution.resolve(session, left) == left
    assert await resolution.resolve(session, right) == right
    assert not await fetch(
        session, "SELECT id FROM curated_collection WHERE slug LIKE 'season-group-%'", {}
    )
