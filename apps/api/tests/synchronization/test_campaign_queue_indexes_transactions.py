import json

import pytest

from api.contexts.synchronization import campaigns
from api.db import fetch


@pytest.mark.asyncio
async def test_pending_work_has_ordered_index_paths_for_each_stage(integration_session):
    session = integration_session
    identifier = await campaigns.create_campaign(session, provider="bangumi", ai_mode="off")
    await fetch(
        session,
        """
        INSERT INTO sync_work_item
          (id,campaign_id,shard,cursor,status,error,attempt,last_error_code,lease_owner,
           ai_processed_at,created_at,updated_at)
        SELECT gen_random_uuid(),:id,1,i::text,
          CASE WHEN i<=1000 THEN 'queued' ELSE 'succeeded' END,'',0,'','',
          CASE WHEN i>2000 THEN now() ELSE NULL END,now(),now()
        FROM generate_series(1,3000) i RETURNING id
    """,
        {"id": identifier},
    )
    # These settings verify that each ordered access path is available independently of
    # planner estimates on a small, rollback-only fixture.
    await fetch(session, "SELECT set_config('enable_seqscan','off',true)", {})
    await fetch(session, "SELECT set_config('enable_sort','off',true)", {})
    for predicate, expected in [
        (
            "status='queued' AND (next_retry_at IS NULL OR next_retry_at<=clock_timestamp())",
            "idx_sync_wi_queued_order",
        ),
        ("status='succeeded' AND ai_processed_at IS NULL", "idx_sync_wi_normalize_order"),
        ("status='succeeded' AND ai_enriched_at IS NULL", "idx_sync_wi_enrich_order"),
    ]:
        plan = await fetch(
            session,
            "EXPLAIN (FORMAT JSON) SELECT id FROM sync_work_item "
            f"WHERE campaign_id=:id AND {predicate} ORDER BY shard,id LIMIT 1",
            {"id": identifier},
        )
        assert expected in json.dumps(plan[0][0])
    rows = await fetch(
        session,
        """
        SELECT c.relname,i.indisvalid FROM pg_index i JOIN pg_class c ON c.oid=i.indexrelid
        WHERE c.relname=ANY(:names)
    """,
        {
            "names": [
                "idx_sync_wi_queued_order",
                "idx_sync_wi_normalize_order",
                "idx_sync_wi_enrich_order",
            ]
        },
    )
    assert len(rows) == 3 and all(row.indisvalid for row in rows)
