"""Append-only agent messages and their native tool-calling representation."""

import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.presentation.fragments import fetch


async def append(
    session: AsyncSession,
    *,
    run_id: UUID,
    role: str,
    content: str = "",
    name: str = "",
    tool_call_id: str = "",
    tool_calls: list[dict[str, Any]] | None = None,
) -> None:
    rows = await fetch(session, "SELECT id FROM agent_run WHERE id=:id FOR UPDATE", {"id": run_id})
    if not rows:
        raise LookupError("Agent run not found.")
    payload = {
        "role": role,
        "content": content[:2_000_000],
        "name": name[:128],
        "tool_call_id": tool_call_id[:128],
        "tool_calls": tool_calls or [],
    }
    digest = hashlib.sha256(
        json.dumps(
            payload, sort_keys=True, ensure_ascii=False, default=str, separators=(",", ":")
        ).encode()
    ).hexdigest()
    await fetch(
        session,
        "INSERT INTO agent_message "
        "(id,run_id,sequence,role,content,name,tool_call_id,tool_calls,content_hash,created_at) "
        "VALUES (gen_random_uuid(),:run,COALESCE((SELECT max(sequence) "
        "FROM agent_message WHERE run_id=:run),0)+1,"
        ":role,:content,:name,:call,CAST(:calls AS jsonb),:hash,now()) RETURNING id",
        {
            "run": run_id,
            "role": role,
            "content": payload["content"],
            "name": payload["name"],
            "call": payload["tool_call_id"],
            "calls": json.dumps(payload["tool_calls"]),
            "hash": digest,
        },
    )


def provider_messages(rows: list[Any]) -> list[dict[str, Any]]:
    messages = []
    for row in rows:
        message = {"role": row.role, "content": row.content or ""}
        if row.role == "assistant" and row.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call["id"],
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": json.dumps(call.get("arguments") or {}, ensure_ascii=False),
                    },
                }
                for call in row.tool_calls
            ]
        if row.role == "tool":
            message.update({"tool_call_id": row.tool_call_id, "name": row.name or ""})
        messages.append(message)
    return messages


async def messages(session: AsyncSession, run_id: UUID) -> list[dict[str, Any]]:
    rows = await fetch(
        session, "SELECT * FROM agent_message WHERE run_id=:id ORDER BY sequence", {"id": run_id}
    )
    return provider_messages(rows)
