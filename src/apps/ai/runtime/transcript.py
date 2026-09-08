"""Append-only transcript helpers for open-ended agent loops."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from apps.ai.models import AgentMessage, AgentRun


def append_message(
    *,
    run: AgentRun,
    role: str,
    content: str = "",
    name: str = "",
    tool_call_id: str = "",
    tool_calls: list[dict[str, Any]] | None = None,
) -> AgentMessage:
    """Persist the next transcript event for ``run`` atomically."""
    sequence = (
        AgentMessage.objects.filter(run=run)
        .values_list("sequence", flat=True)
        .order_by("-sequence")
        .first()
    )
    next_sequence = int(sequence or 0) + 1
    payload = {
        "role": role,
        "content": content,
        "name": name,
        "tool_call_id": tool_call_id,
        "tool_calls": tool_calls or [],
    }
    return AgentMessage.objects.create(
        run=run,
        sequence=next_sequence,
        role=role,
        content=content[:2_000_000],
        name=name[:128],
        tool_call_id=tool_call_id[:128],
        tool_calls=tool_calls or [],
        content_hash=_hash_message(payload),
    )


def messages_for_provider(run: AgentRun) -> list[dict[str, Any]]:
    """Rebuild OpenAI-style chat messages from the durable transcript."""
    rows = AgentMessage.objects.filter(run=run).order_by("sequence")
    messages: list[dict[str, Any]] = []
    for row in rows:
        if row.role == AgentMessage.Role.ASSISTANT:
            message: dict[str, Any] = {
                "role": "assistant",
                "content": row.content or "",
            }
            if row.tool_calls:
                message["tool_calls"] = [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(
                                call.get("arguments") or {},
                                ensure_ascii=False,
                            ),
                        },
                    }
                    for call in row.tool_calls
                ]
            messages.append(message)
            continue
        if row.role == AgentMessage.Role.TOOL:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": row.tool_call_id,
                    "content": row.content or "",
                    "name": row.name or "",
                }
            )
            continue
        messages.append(
            {
                "role": row.role,
                "content": row.content or "",
            }
        )
    return messages


def _hash_message(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
