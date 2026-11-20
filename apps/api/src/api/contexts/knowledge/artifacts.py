"""Content-addressed evidence capture shared by search tools and agent workflows."""

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch


@dataclass(frozen=True, slots=True)
class Artifact:
    id: UUID
    source_url: str
    content_hash: str
    excerpt: str
    metadata: dict[str, Any]


async def capture(
    session: AsyncSession,
    *,
    payload: Any,
    kind: str,
    source_url: str = "",
    tool_name: str = "",
    tool_version: str = "",
    metadata: dict[str, Any] | None = None,
    invocation_id: UUID | None = None,
) -> Artifact:
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    encoded = text.encode()
    details = {
        **(metadata or {}),
        **({"tool_name": tool_name} if tool_name else {}),
        **({"tool_version": tool_version} if tool_version else {}),
    }
    rows = await fetch(
        session,
        """
        INSERT INTO source_artifact
          (id,tool_invocation_id,kind,source_url,content_hash,mime_type,byte_size,
           excerpt,object_key,metadata,license_info,fetched_at,created_at)
        VALUES (gen_random_uuid(),:invocation,:kind,:url,:hash,'application/json',
          :size,:excerpt,'',CAST(:metadata AS jsonb),'',clock_timestamp(),clock_timestamp())
        RETURNING id,source_url,content_hash,excerpt,metadata
        """,
        {
            "invocation": invocation_id,
            "kind": kind,
            "url": source_url,
            "hash": hashlib.sha256(encoded).hexdigest(),
            "size": len(encoded),
            "excerpt": text[:8000],
            "metadata": json.dumps(details),
        },
    )
    return Artifact(**rows[0]._mapping)
