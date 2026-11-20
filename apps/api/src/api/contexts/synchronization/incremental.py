"""Bangumi incremental windows guarded by the state row's update version."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from api.contexts.synchronization.domain import LeaseLost
from api.db import fetch

Part = Literal["subject", "episodes", "subjects", "staff", "characters", "character", "person"]


@dataclass(frozen=True, slots=True)
class TaskConfig:
    name: str
    full_name: str
    namespace: str
    part: Part
    requires_subject: bool = False


CONFIGS = {
    config.name: config
    for config in (
        TaskConfig("incremental_subject", "full_subject", "subject", "subject"),
        TaskConfig("bangumi_subject_refresh", "full_subject", "subject", "subject"),
        TaskConfig("incremental_episode", "full_episode", "subject", "episodes", True),
        TaskConfig(
            "incremental_subject_subject_relation",
            "full_subject_subject_relation",
            "subject",
            "subjects",
            True,
        ),
        TaskConfig(
            "incremental_subject_staff_relation",
            "full_subject_staff_relation",
            "subject",
            "staff",
            True,
        ),
        TaskConfig(
            "incremental_subject_character_relation",
            "full_subject_character_relation",
            "subject",
            "characters",
            True,
        ),
        TaskConfig("incremental_character", "full_character", "character", "character"),
        TaskConfig("incremental_staff", "full_staff", "person", "person"),
    )
}


class AlreadyRunning(RuntimeError):
    """The incremental window is already owned by another invocation."""


@dataclass(slots=True)
class Window:
    config: TaskConfig
    start: int
    end: int
    version: datetime


async def start_window(session: AsyncSession, config: TaskConfig, size: int) -> Window:
    existing = await fetch(
        session,
        "SELECT id FROM sync_state WHERE task_name=:name AND shard='main'",
        {"name": config.name},
    )
    if not existing:
        initial = (
            await fetch(
                session,
                "SELECT COALESCE(NULLIF((SELECT max(r.external_id::integer) FROM provider_record r "
                "JOIN provider_namespace ns ON ns.id=r.namespace_id "
                "JOIN provider p ON p.id=ns.provider_id "
                "WHERE p.slug='bangumi' AND ns.slug=:namespace AND r.status='active' "
                "AND r.external_id ~ '^[0-9]+$'),0), "
                "(SELECT max(end_id) FROM sync_state "
                "WHERE task_name=:full AND status='finished'),0) AS n",
                {"namespace": config.namespace, "full": config.full_name},
            )
        )[0].n
        await fetch(
            session,
            "INSERT INTO sync_state "
            "(task_name,shard,current_id,end_id,status,fail_count,updated_at) "
            "VALUES (:name,'main',:initial,:initial,'idle',0,clock_timestamp()) "
            "ON CONFLICT (task_name,shard) DO NOTHING RETURNING id",
            {"name": config.name, "initial": initial},
        )
    row = (
        await fetch(
            session,
            "SELECT * FROM sync_state WHERE task_name=:name AND shard='main' FOR UPDATE",
            {"name": config.name},
        )
    )[0]
    if row.status == "running":
        raise AlreadyRunning("Incremental sync task is already running.")
    start = row.current_id + 1
    end = row.current_id + max(1, size)
    version = (
        await fetch(
            session,
            "UPDATE sync_state SET end_id=:end,status='running',updated_at=clock_timestamp() "
            "WHERE id=:id RETURNING updated_at",
            {"id": row.id, "end": end},
        )
    )[0].updated_at
    return Window(config, start, end, version)


async def owned(session: AsyncSession, window: Window) -> Any:
    rows = await fetch(
        session,
        "SELECT id FROM sync_state WHERE task_name=:name AND shard='main' "
        "AND status='running' AND updated_at=:version FOR UPDATE",
        {"name": window.config.name, "version": window.version},
    )
    if not rows:
        raise LeaseLost("Incremental sync window changed while retrieving source data.")
    return rows[0].id


async def advance(
    session: AsyncSession, window: Window, current: int, *, status: str = "running"
) -> datetime:
    identifier = await owned(session, window)
    rows = await fetch(
        session,
        "UPDATE sync_state SET current_id=:current,status=CAST(:status AS text),"
        "updated_at=clock_timestamp(),fail_count=fail_count+"
        "CASE WHEN CAST(:status AS text)='failed' THEN 1 ELSE 0 END WHERE id=:id "
        "RETURNING updated_at",
        {"id": identifier, "current": current, "status": status},
    )
    version: datetime = rows[0].updated_at
    return version


async def subject_exists(session: AsyncSession, identifier: int) -> bool:
    return bool(
        await fetch(
            session,
            "SELECT 1 FROM entity_representation rep "
            "JOIN provider_record r ON r.id=rep.provider_record_id "
            "JOIN provider_namespace ns ON ns.id=r.namespace_id "
            "JOIN provider p ON p.id=ns.provider_id "
            "WHERE p.slug='bangumi' AND ns.slug='subject' AND r.external_id=:id "
            "AND r.status='active' AND rep.is_active LIMIT 1",
            {"id": str(identifier)},
        )
    )


async def record_error(session: AsyncSession, name: str, identifier: int) -> None:
    await fetch(
        session,
        "INSERT INTO sync_error "
        "(task_name,entity_id,retry_count,first_occurred_at,last_occurred_at) "
        "VALUES (:name,:id,0,now(),now()) ON CONFLICT (task_name,entity_id) DO UPDATE "
        "SET retry_count=sync_error.retry_count+1,last_occurred_at=now() RETURNING id",
        {"name": name, "id": identifier},
    )
