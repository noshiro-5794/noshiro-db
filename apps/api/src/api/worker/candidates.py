"""Resumable cross-provider candidate generation and structured matching evidence."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import fetch

SWEEP_TASK_NAME = "match_candidate_sweep"
POLICY_VERSION = "title-similarity-v2"
MAX_NAMES_PER_SIDE = 8
MAX_LINKS_PER_SIDE = 6
STRUCTURED_PREDICATES = ("release-date", "episode-count", "platform")
NAME_RANK = {"original": 0, "official": 1, "romanized": 2, "short": 3, "alias": 4, "translated": 5}


class ProviderCandidateService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def generate_candidates(
        self,
        *,
        source_provider: str = "anilist",
        source_namespace: str = "anime",
        target_provider: str = "bangumi",
        target_namespace: str = "subject",
        source_work_types: tuple[str, ...] = ("anime",),
        target_work_types: tuple[str, ...] = ("anime",),
        min_similarity: float | None = None,
        eval_min_similarity: float | None = None,
        top_k: int | None = None,
        create: bool = True,
        limit: int | None = None,
        skip_processed: bool = True,
        max_names_per_side: int = MAX_NAMES_PER_SIDE,
    ) -> dict[str, Any]:
        """Propose pairs for the next window of the source catalogue.

        One trigram lookup runs per source name, so the window bounds the work a
        single run does; the cursor stored in ``SyncState`` makes the next run
        continue where this one stopped instead of re-reading the front of the
        catalogue.
        """
        min_similarity = (
            float(os.environ.get("MATCH_CANDIDATE_MIN_SIMILARITY", "0.3"))
            if min_similarity is None
            else float(min_similarity)
        )
        eval_floor = (
            float(os.environ.get("MATCH_CANDIDATE_EVAL_MIN_SIMILARITY", "0.5"))
            if eval_min_similarity is None
            else float(eval_min_similarity)
        )
        eval_floor = max(eval_floor, min_similarity)
        top_k = int(os.environ.get("MATCH_CANDIDATE_TOP_K", "20")) if top_k is None else int(top_k)
        batch = int(
            limit
            if limit is not None
            else int(os.environ.get("MATCH_CANDIDATE_BATCH_SIZE", "2000"))
        )
        policy_version = POLICY_VERSION
        shard = sweep_shard(
            source_provider=source_provider,
            source_namespace=source_namespace,
            target_provider=target_provider,
            target_namespace=target_namespace,
        )

        if create:
            await self.session.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:scope, 0))"),
                {"scope": f"{SWEEP_TASK_NAME}:{shard}"},
            )
        window, cursor, total, completed_pass = await self._sweep_window(
            source_provider=source_provider,
            source_namespace=source_namespace,
            source_work_types=tuple(source_work_types),
            shard=shard,
            batch=batch,
        )
        summary: dict[str, Any] = {
            "source_provider": source_provider,
            "target_provider": target_provider,
            "policy_version": policy_version,
            "source_work_types": list(source_work_types),
            "target_work_types": list(target_work_types),
            "min_similarity": min_similarity,
            "eval_min_similarity": eval_floor,
            "top_k": top_k,
            "cursor_before": cursor,
            "cursor_after": cursor,
            "window": len(window),
            "catalogue_size": total,
            "completed_pass": completed_pass,
            "source_entities": 0,
            "skipped_processed": 0,
            "candidates_created": 0,
            "conflicting_pairs": 0,
            "pairs_blocked": 0,
            "pairs_below_floor": 0,
            "created_ids": [],
            "pairs": [],
        }
        if not window:
            if create and completed_pass:
                await self._write_cursor(shard=shard, cursor=0, total=total)
                summary["cursor_after"] = 0
            return summary

        window_end = window[-1][1]
        if skip_processed:
            window = await self._drop_decided(
                window=window,
                policy_version=policy_version,
                summary=summary,
            )
        names_by_entity = await self._names_for_entities(
            [entity_id for entity_id, _ in window],
            limit=max_names_per_side,
        )
        for entity_id, _ordinal in window:
            summary["source_entities"] += 1
            names = names_by_entity.get(str(entity_id)) or []
            if not names:
                continue
            best, margin = await self._best_target_matches(
                names=names,
                target_provider=target_provider,
                target_namespace=target_namespace,
                target_work_types=tuple(target_work_types),
                min_similarity=min_similarity,
                top_k=top_k,
            )
            if not best:
                continue
            # Blocking is permissive on purpose, but only pairs worth a decision
            # become candidates: everything above the evaluation floor, or the
            # single best hit when nothing clears it. Writing all twenty blocked
            # pairs would queue twenty model calls for one work, nineteen of them
            # known to be wrong, and the low ones would also mark the source as
            # decided on the next pass.
            above_floor = [match for match in best if match["similarity"] >= eval_floor]
            selected = above_floor or best[:1]
            summary["pairs_blocked"] += len(best)
            summary["pairs_below_floor"] += len(best) - len(above_floor)
            attributes = await self._attributes_for_entities(
                [str(entity_id), *(match["entity_id"] for match in selected)]
            )
            source_attributes = attributes.get(str(entity_id), {})
            for match in selected:
                target_attributes = attributes.get(match["entity_id"], {})
                comparison, conflicts = self._compare(
                    source=source_attributes, target=target_attributes
                )
                summary["pairs"].append(
                    {
                        "source_entity": str(entity_id),
                        "target_entity": match["entity_id"],
                        "source_text": match["source_text"],
                        "target_text": match["target_text"],
                        "similarity": round(match["similarity"], 4),
                        "margin": round(margin, 4),
                        "hard_conflicts": len(conflicts),
                    }
                )
                if conflicts:
                    summary["conflicting_pairs"] += 1
                if not create:
                    continue
                created = await self._create_candidate(
                    source_entity_id=str(entity_id),
                    target_entity_id=match["entity_id"],
                    policy_version=policy_version,
                    source_text=match["source_text"],
                    target_text=match["target_text"],
                    similarity=match["similarity"],
                    margin=margin,
                    provider_pair=f"{source_provider}:{target_provider}",
                    source_attributes=source_attributes,
                    target_attributes=target_attributes,
                    comparison=comparison,
                    conflicts=conflicts,
                )
                if created is not None:
                    summary["candidates_created"] += 1
                    summary["created_ids"].append(created)
        # The window is idempotent - a run that dies half way only redoes it - so
        # the cursor is written once per run instead of once per entity. A dry run
        # must not move it: nothing was written for the pairs it reported.
        if create and window_end > cursor:
            await self._write_cursor(shard=shard, cursor=window_end, total=total)
            summary["cursor_after"] = window_end
        return summary

    async def generate_anime_candidates(self, **kwargs: Any) -> dict[str, Any]:
        """AniList anime against Bangumi anime subjects."""
        kwargs.setdefault("source_provider", "anilist")
        kwargs.setdefault("source_namespace", "anime")
        kwargs.setdefault("target_provider", "bangumi")
        kwargs.setdefault("target_namespace", "subject")
        kwargs.setdefault("source_work_types", ("anime",))
        kwargs.setdefault("target_work_types", ("anime",))
        return await self.generate_candidates(**kwargs)

    async def generate_mal_bangumi_candidates(self, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("source_provider", "mal")
        kwargs.setdefault("source_namespace", "anime")
        kwargs.setdefault("target_provider", "bangumi")
        kwargs.setdefault("target_namespace", "subject")
        kwargs.setdefault("source_work_types", ("anime",))
        kwargs.setdefault("target_work_types", ("anime",))
        return await self.generate_candidates(**kwargs)

    async def generate_galgame_candidates(self, **kwargs: Any) -> dict[str, Any]:
        """VNDB visual novels against Bangumi game entries.

        Bangumi files visual novels under its broader ``game`` type and only
        marks the galgame subset with a tag, so the target family is both types
        and the evaluator decides which of them is the same work.
        """
        kwargs.setdefault("source_provider", "vndb")
        kwargs.setdefault("source_namespace", "vn")
        kwargs.setdefault("target_provider", "bangumi")
        kwargs.setdefault("target_namespace", "subject")
        kwargs.setdefault("source_work_types", ("galgame",))
        kwargs.setdefault(
            "target_work_types",
            ("galgame", "game"),
        )
        return await self.generate_candidates(**kwargs)

    @staticmethod
    def _compare(
        *, source: dict[str, Any], target: dict[str, Any]
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """How the two sides agree, and what outright contradicts.

        Only contradictions a human would call a mistake become hard conflicts,
        because a hard conflict blocks every automatic bind path. A release year
        that differs by more than one is one of those: remakes a generation apart
        share a title, and silently collapsing them rewrites history.
        """
        year_delta: int | None = None
        if source.get("release_year") and target.get("release_year"):
            year_delta = abs(int(source["release_year"]) - int(target["release_year"]))
        episode_delta: int | None = None
        if source.get("episode_count") and target.get("episode_count"):
            episode_delta = abs(int(source["episode_count"]) - int(target["episode_count"]))
        comparison = {
            "release_year_delta": year_delta,
            "episode_count_delta": episode_delta,
            "shared_languages": sorted(
                set(source.get("languages") or []) & set(target.get("languages") or [])
            ),
            "has_release_date_on_both_sides": bool(
                source.get("release_date") and target.get("release_date")
            ),
        }
        conflicts: list[dict[str, Any]] = []
        if year_delta is not None and year_delta > 1:
            conflicts.append(
                {
                    "type": "release_year_conflict",
                    "source_year": source.get("release_year"),
                    "target_year": target.get("release_year"),
                    "delta_years": year_delta,
                }
            )
        return comparison, conflicts

    async def _write_cursor(self, *, shard: str, cursor: int, total: int) -> None:
        await fetch(
            self.session,
            """
            INSERT INTO sync_state
              (task_name, shard, current_id, end_id, status, fail_count, updated_at)
            VALUES (:task, :shard, :cursor, :total, 'running', 0, now())
            ON CONFLICT (task_name, shard) DO UPDATE SET current_id = EXCLUDED.current_id,
              end_id = EXCLUDED.end_id, status = EXCLUDED.status, updated_at = now()
            RETURNING id
        """,
            {"task": SWEEP_TASK_NAME, "shard": shard, "cursor": cursor, "total": total},
        )

    async def _sweep_window(
        self,
        *,
        source_provider: str,
        source_namespace: str,
        source_work_types: tuple[str, ...],
        shard: str,
        batch: int,
    ) -> tuple[list[tuple[str, int]], int, int, bool]:
        rows = await fetch(
            self.session,
            "SELECT current_id FROM sync_state WHERE task_name = :task AND shard = :shard",
            {"task": SWEEP_TASK_NAME, "shard": shard},
        )
        cursor = int(rows[0].current_id) if rows else 0
        rows = await fetch(
            self.session,
            """
            WITH source AS (
              SELECT DISTINCT e.id AS entity_id, e.created_at
              FROM entity e JOIN entity_representation rep ON rep.entity_id = e.id AND rep.is_active
              JOIN provider_record r ON r.id = rep.provider_record_id
              JOIN provider_namespace ns ON ns.id = r.namespace_id
              JOIN provider p ON p.id = ns.provider_id
              JOIN work w ON w.entity_id = e.id
              WHERE ns.slug = :namespace AND p.slug = :provider AND w.work_type = ANY(:types)
            ), ordered AS (
              SELECT entity_id, row_number() OVER (ORDER BY created_at, entity_id) AS rn,
                     count(*) OVER () AS total FROM source
            ) SELECT entity_id, rn, total FROM ordered WHERE rn > :cursor ORDER BY rn LIMIT :batch
        """,
            {
                "namespace": source_namespace,
                "provider": source_provider,
                "types": list(source_work_types),
                "cursor": cursor,
                "batch": max(1, batch),
            },
        )
        if not rows:
            # Reading a dry-run window must not reset persisted progress.
            return [], cursor, cursor, cursor > 0
        return (
            [(str(row.entity_id), int(row.rn)) for row in rows],
            cursor,
            int(rows[0].total),
            False,
        )

    async def _drop_decided(
        self, *, window: list[tuple[str, int]], policy_version: str, summary: dict[str, Any]
    ) -> list[tuple[str, int]]:
        rows = await fetch(
            self.session,
            """
            SELECT left_entity_id, right_entity_id FROM match_candidate
            WHERE policy_version = :policy AND status = ANY(:statuses)
        """,
            {"policy": policy_version, "statuses": ["pending", "accepted", "grouped"]},
        )
        decided = {
            str(value) for row in rows for value in (row.left_entity_id, row.right_entity_id)
        }
        kept = [(entity_id, ordinal) for entity_id, ordinal in window if entity_id not in decided]
        summary["skipped_processed"] = len(window) - len(kept)
        return kept

    async def _names_for_entities(
        self, entity_ids: list[str], *, limit: int
    ) -> dict[str, list[str]]:
        rows = await fetch(
            self.session,
            """
            SELECT entity_id, text FROM entity_name WHERE entity_id = ANY(:ids) AND text <> ''
            ORDER BY entity_id, kind, language, id
        """,
            {"ids": [UUID(value) for value in entity_ids]},
        )
        names: dict[str, list[str]] = defaultdict(list)
        seen: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            key = str(row.entity_id)
            normalized = " ".join(str(row.text).split())
            folded = normalized.casefold()
            if normalized and folded not in seen[key] and len(names[key]) < limit:
                seen[key].add(folded)
                names[key].append(normalized[:512])
        return names

    async def _best_target_matches(
        self,
        *,
        names: list[str],
        target_provider: str,
        target_namespace: str,
        target_work_types: tuple[str, ...],
        min_similarity: float,
        top_k: int,
    ) -> tuple[list[dict[str, Any]], float]:
        best: dict[str, dict[str, Any]] = {}
        for name in names:
            rows = await fetch(
                self.session,
                """
                SELECT en.entity_id, en.text, similarity(en.text, :name) AS sim
                FROM entity_name en
                JOIN entity_representation rep ON rep.entity_id = en.entity_id AND rep.is_active
                JOIN provider_record r ON r.id = rep.provider_record_id
                JOIN provider_namespace ns ON ns.id = r.namespace_id
                JOIN provider p ON p.id = ns.provider_id
                JOIN work w ON w.entity_id = en.entity_id
                WHERE ns.slug = :namespace AND p.slug = :provider AND w.work_type = ANY(:types)
                  AND btrim(en.text) <> '' AND en.text % :name
                  AND similarity(en.text, :name) >= :minimum
                ORDER BY sim DESC, en.entity_id LIMIT :limit
            """,
                {
                    "name": name,
                    "namespace": target_namespace,
                    "provider": target_provider,
                    "types": list(target_work_types),
                    "minimum": min_similarity,
                    "limit": top_k,
                },
            )
            for row in rows:
                key = str(row.entity_id)
                if key not in best or float(row.sim) > best[key]["similarity"]:
                    best[key] = {
                        "entity_id": key,
                        "text": row.text,
                        "similarity": float(row.sim),
                        "source_text": name,
                        "target_text": row.text,
                    }
        ordered = sorted(best.values(), key=lambda item: (-item["similarity"], item["entity_id"]))
        margin = (
            max(0.0, ordered[0]["similarity"] - ordered[1]["similarity"])
            if len(ordered) > 1
            else 0.0
        )
        return ordered, margin

    async def _attributes_for_entities(self, entity_ids: list[str]) -> dict[str, dict[str, Any]]:
        ids = [UUID(value) for value in dict.fromkeys(entity_ids)]
        attributes: dict[str, dict[str, Any]] = {
            str(value): {
                "names": [],
                "languages": [],
                "release_date": None,
                "release_year": None,
                "episode_count": None,
                "platform": None,
                "links": [],
            }
            for value in ids
        }
        rows = await fetch(
            self.session,
            "SELECT entity_id, text, language, kind FROM entity_name "
            "WHERE entity_id = ANY(:ids) AND text <> ''",
            {"ids": ids},
        )
        names: dict[str, list[tuple[int, str]]] = defaultdict(list)
        languages: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            key = str(row.entity_id)
            normalized = " ".join(str(row.text).split())
            if normalized:
                names[key].append((NAME_RANK.get(row.kind, 9), normalized[:512]))
                if row.language:
                    languages[key].add(str(row.language))
        for key, values in names.items():
            seen: set[str] = set()
            for _, value in sorted(values):
                if value.casefold() not in seen:
                    seen.add(value.casefold())
                    attributes[key]["names"].append(value)
                    if len(attributes[key]["names"]) >= MAX_NAMES_PER_SIDE:
                        break
        for key, language_values in languages.items():
            attributes[key]["languages"] = sorted(language_values)
        rows = await fetch(
            self.session,
            """
            SELECT f.entity_id, p.slug, f.value FROM fact f
            JOIN predicate p ON p.id = f.predicate_id
            WHERE f.entity_id = ANY(:ids) AND p.slug = ANY(:predicates) AND f.status = 'selected'
        """,
            {"ids": ids, "predicates": list(STRUCTURED_PREDICATES)},
        )
        for row in rows:
            item = attributes[str(row.entity_id)]
            if row.slug == "release-date":
                item["release_date"], item["release_year"] = (
                    _as_iso_date(row.value),
                    _as_year(row.value),
                )
            elif row.slug == "episode-count":
                item["episode_count"] = _as_int(row.value)
            elif row.slug == "platform":
                item["platform"] = _as_text(row.value)
        rows = await fetch(
            self.session,
            "SELECT work_id, premiered_on, episode_count, format FROM anime_profile "
            "WHERE work_id = ANY(:ids)",
            {"ids": ids},
        )
        for row in rows:
            item = attributes[str(row.work_id)]
            if item["release_date"] is None and row.premiered_on is not None:
                item["release_date"], item["release_year"] = (
                    row.premiered_on.isoformat(),
                    row.premiered_on.year,
                )
            if item["episode_count"] is None and row.episode_count:
                item["episode_count"] = int(row.episode_count)
            if item["platform"] is None and row.format:
                item["platform"] = str(row.format)
        rows = await fetch(
            self.session,
            "SELECT entity_id, url FROM external_link WHERE entity_id = ANY(:ids) "
            "ORDER BY entity_id, id",
            {"ids": ids},
        )
        for row in rows:
            links = attributes[str(row.entity_id)]["links"]
            if len(links) < MAX_LINKS_PER_SIDE:
                links.append(str(row.url))
        return attributes

    async def _create_candidate(
        self,
        *,
        source_entity_id: str,
        target_entity_id: str,
        policy_version: str,
        source_text: str,
        target_text: str,
        similarity: float,
        margin: float,
        provider_pair: str,
        source_attributes: dict[str, Any],
        target_attributes: dict[str, Any],
        comparison: dict[str, Any],
        conflicts: list[dict[str, Any]],
    ) -> str | None:
        left, right = sorted((UUID(source_entity_id), UUID(target_entity_id)), key=str)
        async with self.session.begin_nested():
            rows = await fetch(
                self.session,
                """
                INSERT INTO match_candidate (id, left_entity_id, right_entity_id, policy_version,
                  score, runner_up_margin, status, hard_conflicts, created_at, updated_at)
                VALUES (gen_random_uuid(), :left, :right, :policy, :score, :margin, 'pending',
                  CAST(:conflicts AS jsonb), now(), now())
                ON CONFLICT (left_entity_id, right_entity_id, policy_version) DO NOTHING
                RETURNING id
            """,
                {
                    "left": left,
                    "right": right,
                    "policy": policy_version,
                    "score": round(min(max(similarity, 0.0), 1.0), 4),
                    "margin": round(min(max(margin, 0.0), 1.0), 4),
                    "conflicts": json.dumps(conflicts),
                },
            )
            if not rows:
                return None
            candidate_id = rows[0].id
            for kind, value, weight in (
                (
                    "title_similarity",
                    {
                        "provider_pair": provider_pair,
                        "source_text": source_text,
                        "target_text": target_text,
                        "similarity": round(similarity, 4),
                    },
                    round(min(max(similarity, 0.0), 1.0), 4),
                ),
                (
                    "work_attributes",
                    {
                        "provider_pair": provider_pair,
                        "source_entity_id": source_entity_id,
                        "target_entity_id": target_entity_id,
                        "source": source_attributes,
                        "target": target_attributes,
                        "comparison": comparison,
                    },
                    1,
                ),
            ):
                await fetch(
                    self.session,
                    """
                    INSERT INTO match_evidence
                      (candidate_id, evidence_type, value, weight, created_at, updated_at)
                    VALUES (:candidate, :kind, CAST(:value AS jsonb), :weight, now(), now())
                    RETURNING id
                """,
                    {
                        "candidate": candidate_id,
                        "kind": kind,
                        "value": json.dumps(value),
                        "weight": weight,
                    },
                )
        return str(candidate_id)


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_iso_date(value: Any) -> str | None:
    text = _as_text(value)
    if text is None:
        return None
    return text[:10]


def _as_year(value: Any) -> int | None:
    text = _as_text(value)
    if text is None or len(text) < 4:
        return None
    year = _as_int(text[:4])
    return year if year and 1900 <= year <= 2200 else None


def sweep_shard(
    *, source_provider: str, source_namespace: str, target_provider: str, target_namespace: str
) -> str:
    return f"{source_provider}:{source_namespace}->{target_provider}:{target_namespace}"
