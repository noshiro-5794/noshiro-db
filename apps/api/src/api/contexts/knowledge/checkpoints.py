"""Serializable snapshots of agent progress for terminal states and replay."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch


async def capture(
    session: AsyncSession, run_id: UUID, *, now: datetime | None = None
) -> dict[str, Any]:
    runs = await fetch(session, "SELECT status FROM agent_run WHERE id=:id", {"id": run_id})
    if not runs:
        raise LookupError("Agent run not found.")
    rows = await fetch(
        session,
        "SELECT id,sequence,kind,status,parent_id,skill_name,skill_version,input_hash,input,output,"
        "error,retry_count FROM agent_step WHERE run_id=:id ORDER BY sequence",
        {"id": run_id},
    )
    steps = []
    for row in rows:
        step = dict(row._mapping)
        step["id"] = str(step["id"])
        step["parent_id"] = str(step["parent_id"]) if step["parent_id"] else None
        step["input"] = step["input"] or {}
        steps.append(step)
    count = (
        await fetch(
            session, "SELECT count(*) AS n FROM agent_message WHERE run_id=:id", {"id": run_id}
        )
    )[0].n
    result = {
        "run_id": str(run_id),
        "run_status": runs[0].status,
        "step_count": len(steps),
        "message_count": count,
        "last_completed_sequence": max(
            (step["sequence"] for step in steps if step["status"] == "succeeded"), default=-1
        ),
        "steps": steps,
        "captured_at": (now or datetime.now(UTC)).isoformat(),
    }
    result["content_hash"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()
    return result
