"""Cross-provider work candidate generation.

This service only *proposes* pairs; a decision is always someone else's - an
official external id, the AI evaluator plus its policy, or an administrator.

Three properties matter:

* **Scope.** Candidates are raised inside a matchable work family only: anime
  against anime, galgame against galgame or the broader ``game`` type (see
  :mod:`apps.index.services.work_families`). Characters, episodes, releases and
  contributors are per-provider records whose identity follows their parent work.
* **Resumability.** The sweep walks the source catalogue in a stable order -
  ``(entity.created_at, entity.id)``, so a newly imported entity lands at the end
  instead of somewhere in the middle - and records how far it got in
  ``SyncState``. The previous version restarted from the beginning on every run
  and only removed entities that had produced a candidate, so entities that
  matched nothing stayed permanently at the front of the queue: 14,359 of 22,003
  AniList anime had never been searched at all.
* **Blocking is cheap, precision lives in the evidence.** Blocking is pg_trgm
  over every stored name with a deliberately permissive threshold and a wide
  top-k, because a pair that is never proposed can never be reviewed. The
  structured evidence written alongside it (release date, episode count,
  platform, every name on both sides) is what lets the evaluator - and the
  policy gates, which refuse to bind on any hard conflict - reach a decision.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from django.conf import settings
from django.db import connection, transaction

from apps.index.models import (
    AnimeProfile,
    EntityName,
    ExternalLink,
    Fact,
    MatchCandidate,
    MatchEvidence,
    Work,
)
from apps.sync.models import SyncState

SWEEP_TASK_NAME = "match_candidate_sweep"

# Bumped because the evidence changed shape: v1 candidates carry a single title
# similarity and no structured attributes, so they cannot be re-decided by the
# new evaluator. A new version gives every work one fresh pass.
POLICY_VERSION = "title-similarity-v2"

# The evaluator may only bind a pair it can corroborate, so the generator writes
# everything the catalogue knows about the two sides for it to reason over.
MAX_NAMES_PER_SIDE = 8
MAX_LINKS_PER_SIDE = 6
STRUCTURED_PREDICATES = ("release-date", "episode-count", "platform")

# Name kinds in the order a reader would recognise them; ``original`` is the
# provider's own title, aliases are last because they are often translations or
# disambiguation strings rather than the work's name.
_NAME_KIND_RANK = {
    EntityName.Kind.ORIGINAL: 0,
    EntityName.Kind.OFFICIAL: 1,
    EntityName.Kind.ROMANIZED: 2,
    EntityName.Kind.SHORT: 3,
    EntityName.Kind.ALIAS: 4,
    EntityName.Kind.TRANSLATED: 5,
}


def _work_type_clause(work_types: tuple[str, ...]) -> tuple[str, list[str]]:
    """A validated ``IN`` clause for a set of work types.

    The values come from a TextChoices enum, but they are still checked against it
    so the fragment can never carry anything but a known work type.
    """
    allowed = {value for value, _ in Work.WorkType.choices}
    unknown = set(work_types) - allowed
    if unknown:
        raise ValueError(f"Unknown work types: {sorted(unknown)}")
    if not work_types:
        raise ValueError("At least one work type is required.")
    placeholders = ", ".join(["%s"] * len(work_types))
    return f"({placeholders})", list(work_types)


class ProviderCandidateService:
    POLICY_VERSION = POLICY_VERSION

    def generate_candidates(
        self,
        *,
        source_provider: str = "anilist",
        source_namespace: str = "anime",
        target_provider: str = "bangumi",
        target_namespace: str = "subject",
        source_work_types: tuple[str, ...] = (Work.WorkType.ANIME,),
        target_work_types: tuple[str, ...] = (Work.WorkType.ANIME,),
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
            settings.MATCH_CANDIDATE_MIN_SIMILARITY
            if min_similarity is None
            else float(min_similarity)
        )
        eval_floor = (
            settings.MATCH_CANDIDATE_EVAL_MIN_SIMILARITY
            if eval_min_similarity is None
            else float(eval_min_similarity)
        )
        eval_floor = max(eval_floor, min_similarity)
        top_k = settings.MATCH_CANDIDATE_TOP_K if top_k is None else int(top_k)
        batch = int(limit if limit is not None else settings.MATCH_CANDIDATE_BATCH_SIZE)
        policy_version = self._policy_version(source_provider, target_provider)
        shard = self.sweep_shard(
            source_provider=source_provider,
            source_namespace=source_namespace,
            target_provider=target_provider,
            target_namespace=target_namespace,
        )

        window, cursor, total, completed_pass = self._sweep_window(
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
            return summary

        if skip_processed:
            window = self._drop_decided(
                window=window,
                policy_version=policy_version,
                summary=summary,
            )
        names_by_entity = self._names_for_entities(
            [entity_id for entity_id, _ in window],
            limit=max_names_per_side,
        )
        last_ordinal = cursor
        for entity_id, ordinal in window:
            summary["source_entities"] += 1
            last_ordinal = ordinal
            names = names_by_entity.get(str(entity_id)) or []
            if not names:
                continue
            best, margin = self._best_target_matches(
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
            attributes = self._attributes_for_entities(
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
                created = self._create_candidate(
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
        if create and last_ordinal > cursor:
            self._write_cursor(shard=shard, cursor=last_ordinal, total=total)
            summary["cursor_after"] = last_ordinal
        return summary

    def generate_anime_candidates(self, **kwargs: Any) -> dict[str, Any]:
        """AniList anime against Bangumi anime subjects."""
        kwargs.setdefault("source_provider", "anilist")
        kwargs.setdefault("source_namespace", "anime")
        kwargs.setdefault("target_provider", "bangumi")
        kwargs.setdefault("target_namespace", "subject")
        kwargs.setdefault("source_work_types", (Work.WorkType.ANIME,))
        kwargs.setdefault("target_work_types", (Work.WorkType.ANIME,))
        return self.generate_candidates(**kwargs)

    def generate_mal_bangumi_candidates(self, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("source_provider", "mal")
        kwargs.setdefault("source_namespace", "anime")
        kwargs.setdefault("target_provider", "bangumi")
        kwargs.setdefault("target_namespace", "subject")
        kwargs.setdefault("source_work_types", (Work.WorkType.ANIME,))
        kwargs.setdefault("target_work_types", (Work.WorkType.ANIME,))
        return self.generate_candidates(**kwargs)

    def generate_galgame_candidates(self, **kwargs: Any) -> dict[str, Any]:
        """VNDB visual novels against Bangumi game entries.

        Bangumi files visual novels under its broader ``game`` type and only
        marks the galgame subset with a tag, so the target family is both types
        and the evaluator decides which of them is the same work.
        """
        kwargs.setdefault("source_provider", "vndb")
        kwargs.setdefault("source_namespace", "vn")
        kwargs.setdefault("target_provider", "bangumi")
        kwargs.setdefault("target_namespace", "subject")
        kwargs.setdefault("source_work_types", (Work.WorkType.GALGAME,))
        kwargs.setdefault(
            "target_work_types",
            (Work.WorkType.GALGAME, Work.WorkType.GAME),
        )
        return self.generate_candidates(**kwargs)

    # -- sweep cursor ----------------------------------------------------

    @staticmethod
    def sweep_shard(
        *,
        source_provider: str,
        source_namespace: str,
        target_provider: str,
        target_namespace: str,
    ) -> str:
        return (
            f"{source_provider}:{source_namespace}"
            f"->{target_provider}:{target_namespace}"
        )

    @staticmethod
    def _read_cursor(*, shard: str) -> int:
        state = SyncState.objects.filter(task_name=SWEEP_TASK_NAME, shard=shard).first()
        return int(state.current_id) if state is not None else 0

    @staticmethod
    def _write_cursor(*, shard: str, cursor: int, total: int) -> None:
        SyncState.objects.update_or_create(
            task_name=SWEEP_TASK_NAME,
            shard=shard,
            defaults={
                "current_id": int(cursor),
                "end_id": int(total),
                "status": SyncState.Status.RUNNING,
            },
        )

    def reset_cursor(self, *, shard: str) -> None:
        """Start the next pass from the top of the catalogue."""
        SyncState.objects.filter(task_name=SWEEP_TASK_NAME, shard=shard).update(
            current_id=0
        )

    def _sweep_window(
        self,
        *,
        source_provider: str,
        source_namespace: str,
        source_work_types: tuple[str, ...],
        shard: str,
        batch: int,
    ) -> tuple[list[tuple[str, int]], int, int, bool]:
        """The next ``batch`` source entities after the recorded cursor.

        Returns the window, the cursor it started from, the size of the source
        catalogue, and whether this run closed a full pass (in which case the
        cursor was reset and the caller should do no work this run).
        """
        work_clause, work_params = _work_type_clause(source_work_types)
        query = f"""
            WITH source AS (
                SELECT DISTINCT e.id AS entity_id, e.created_at AS created_at
                FROM entity e
                JOIN entity_representation pr
                  ON pr.entity_id = e.id AND pr.is_active
                JOIN provider_record rec ON rec.id = pr.provider_record_id
                JOIN provider_namespace pn
                  ON pn.id = rec.namespace_id AND pn.slug = %s
                JOIN provider p ON p.id = pn.provider_id AND p.slug = %s
                JOIN work w ON w.entity_id = e.id AND w.work_type IN {work_clause}
            ), ordered AS (
                SELECT entity_id,
                       row_number() OVER (ORDER BY created_at, entity_id) AS rn,
                       count(*) OVER () AS total
                FROM source
            )
            SELECT entity_id, rn, total FROM ordered
            WHERE rn > %s ORDER BY rn LIMIT %s
        """
        params = [
            source_namespace,
            source_provider,
            *work_params,
        ]
        cursor = self._read_cursor(shard=shard)
        with connection.cursor() as db:
            db.execute(query, [*params, cursor, max(1, batch)])
            rows = db.fetchall()
        if not rows:
            if cursor == 0:
                return [], 0, 0, False
            # The pass reached the end of the catalogue. Reset so the next run
            # starts a fresh pass over the works imported since, rather than
            # silently leaving the cursor parked at the end forever.
            self._write_cursor(shard=shard, cursor=0, total=cursor)
            return [], cursor, cursor, True
        total = int(rows[0][2])
        window = [(str(row[0]), int(row[1])) for row in rows]
        return window, cursor, total, False

    def _drop_decided(
        self,
        *,
        window: list[tuple[str, int]],
        policy_version: str,
        summary: dict[str, Any],
    ) -> list[tuple[str, int]]:
        """Drop entities this policy has already proposed and not finished with.

        Abstained and rejected pairs are deliberately *not* dropped: they were
        decided on weaker evidence, and re-proposing them is how a better
        evaluator gets a second look. Pending and accepted ones are kept out so a
        second caller sweeping the same window does not duplicate the AI work.
        """
        decided: set[str] = set()
        rows = MatchCandidate.objects.filter(
            policy_version=policy_version,
            status__in=[
                MatchCandidate.Status.PENDING,
                MatchCandidate.Status.ACCEPTED,
                MatchCandidate.Status.GROUPED,
            ],
        ).values_list("left_entity_id", "right_entity_id")
        for left, right in rows:
            decided.add(str(left))
            decided.add(str(right))
        if not decided:
            return window
        kept = [
            (entity_id, ordinal)
            for entity_id, ordinal in window
            if entity_id not in decided
        ]
        summary["skipped_processed"] = len(window) - len(kept)
        return kept

    # -- blocking --------------------------------------------------------

    @staticmethod
    def _names_for_entities(
        entity_ids: list[str], *, limit: int
    ) -> dict[str, list[str]]:
        names: dict[str, list[str]] = defaultdict(list)
        rows = (
            EntityName.objects.filter(entity_id__in=entity_ids)
            .exclude(text="")
            .order_by("entity_id", "kind", "language", "id")
            .values_list("entity_id", "text")
        )
        seen: dict[str, set[str]] = defaultdict(set)
        for entity_id, text in rows:
            key = str(entity_id)
            normalized = " ".join(str(text).split())
            folded = normalized.casefold()
            if not normalized or folded in seen[key]:
                continue
            if len(names[key]) >= limit:
                continue
            seen[key].add(folded)
            names[key].append(normalized[:512])
        return names

    def _best_target_matches(
        self,
        *,
        names: list[str],
        target_provider: str,
        target_namespace: str,
        target_work_types: tuple[str, ...],
        min_similarity: float,
        top_k: int,
    ) -> tuple[list[dict[str, Any]], float]:
        """Best-scoring target entity per name pair, plus the runner-up margin.

        Every name on the source side is tried, and a target entity keeps its
        best score. The margin between the best and the second best candidate is
        what tells the evaluator that a title is ambiguous - it used to be
        recorded as a constant zero, which threw that signal away.
        """
        best: dict[str, dict[str, Any]] = {}
        for name in names:
            for match in self._target_matches(
                name=name,
                provider_slug=target_provider,
                namespace_slug=target_namespace,
                work_types=target_work_types,
                min_similarity=min_similarity,
                top_k=top_k,
            ):
                key = match["entity_id"]
                current = best.get(key)
                if current is None or match["similarity"] > current["similarity"]:
                    best[key] = {
                        **match,
                        "source_text": name,
                        "target_text": match["text"],
                    }
        ordered = sorted(
            best.values(),
            key=lambda item: (-item["similarity"], item["entity_id"]),
        )
        margin = 0.0
        if len(ordered) > 1:
            margin = max(0.0, ordered[0]["similarity"] - ordered[1]["similarity"])
        return ordered, margin

    @staticmethod
    def _target_matches(
        *,
        name: str,
        provider_slug: str,
        namespace_slug: str,
        work_types: tuple[str, ...],
        min_similarity: float,
        top_k: int,
    ) -> list[dict[str, Any]]:
        work_clause, work_params = _work_type_clause(work_types)
        query = f"""
            SELECT en.entity_id, en.text, similarity(en.text, %s) AS sim
            FROM entity_name en
            JOIN entity_representation pr
              ON pr.entity_id = en.entity_id AND pr.is_active
            JOIN provider_record rec ON rec.id = pr.provider_record_id
            JOIN provider_namespace pn
              ON pn.id = rec.namespace_id AND pn.slug = %s
            JOIN provider p ON p.id = pn.provider_id AND p.slug = %s
            JOIN work w ON w.entity_id = en.entity_id AND w.work_type IN {work_clause}
            WHERE btrim(en.text) <> ''
              AND en.text %% %s
              AND similarity(en.text, %s) >= %s
            ORDER BY sim DESC, en.entity_id
            LIMIT %s
        """
        params = [
            name,
            namespace_slug,
            provider_slug,
            *work_params,
            name,
            name,
            min_similarity,
            top_k,
        ]
        with connection.cursor() as db:
            db.execute(query, params)
            rows = db.fetchall()
        return [
            {"entity_id": str(row[0]), "text": row[1], "similarity": float(row[2])}
            for row in rows
        ]

    # -- evidence --------------------------------------------------------

    def _attributes_for_entities(
        self, entity_ids: list[str]
    ) -> dict[str, dict[str, Any]]:
        """The catalogue's structured picture of each entity, for the evidence."""
        unique = list(dict.fromkeys(str(value) for value in entity_ids))
        attributes: dict[str, dict[str, Any]] = {
            entity_id: {
                "names": [],
                "languages": [],
                "release_date": None,
                "release_year": None,
                "episode_count": None,
                "platform": None,
                "links": [],
            }
            for entity_id in unique
        }
        if not unique:
            return attributes

        names: dict[str, list[tuple[int, str]]] = defaultdict(list)
        languages: dict[str, set[str]] = defaultdict(set)
        for entity_id, text, language, kind in (
            EntityName.objects.filter(entity_id__in=unique)
            .exclude(text="")
            .values_list("entity_id", "text", "language", "kind")
        ):
            key = str(entity_id)
            normalized = " ".join(str(text).split())
            if not normalized:
                continue
            names[key].append((_NAME_KIND_RANK.get(kind, 9), normalized[:512]))
            if language:
                languages[key].add(str(language))
        for key, values in names.items():
            values.sort()
            seen: set[str] = set()
            for _, text in values:
                folded = text.casefold()
                if folded in seen:
                    continue
                seen.add(folded)
                attributes[key]["names"].append(text)
                if len(attributes[key]["names"]) >= MAX_NAMES_PER_SIDE:
                    break
        for key, values in languages.items():
            attributes[key]["languages"] = sorted(values)

        for entity_id, slug, value in Fact.objects.filter(
            entity_id__in=unique,
            predicate__slug__in=STRUCTURED_PREDICATES,
            status=Fact.Status.SELECTED,
        ).values_list("entity_id", "predicate__slug", "value"):
            key = str(entity_id)
            if slug == "release-date":
                attributes[key]["release_date"] = _as_iso_date(value)
                attributes[key]["release_year"] = _as_year(value)
            elif slug == "episode-count":
                attributes[key]["episode_count"] = _as_int(value)
            elif slug == "platform":
                attributes[key]["platform"] = _as_text(value)

        for (
            work_id,
            premiered_on,
            episode_count,
            page_format,
        ) in AnimeProfile.objects.filter(work_id__in=unique).values_list(
            "work_id", "premiered_on", "episode_count", "format"
        ):
            key = str(work_id)
            if attributes[key]["release_date"] is None and premiered_on is not None:
                attributes[key]["release_date"] = premiered_on.isoformat()
                attributes[key]["release_year"] = premiered_on.year
            if attributes[key]["episode_count"] is None and episode_count:
                attributes[key]["episode_count"] = int(episode_count)
            if attributes[key]["platform"] is None and page_format:
                attributes[key]["platform"] = str(page_format)

        links: dict[str, list[str]] = defaultdict(list)
        for entity_id, url in (
            ExternalLink.objects.filter(entity_id__in=unique)
            .order_by("entity_id", "id")
            .values_list("entity_id", "url")
        ):
            key = str(entity_id)
            if len(links[key]) >= MAX_LINKS_PER_SIDE:
                continue
            links[key].append(str(url))
        for key, values in links.items():
            attributes[key]["links"] = values
        return attributes

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
            episode_delta = abs(
                int(source["episode_count"]) - int(target["episode_count"])
            )
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

    @staticmethod
    @transaction.atomic
    def _create_candidate(
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
    ) -> Any:
        left, right = sorted((source_entity_id, target_entity_id), key=str)
        candidate, created = MatchCandidate.objects.get_or_create(
            left_entity_id=left,
            right_entity_id=right,
            policy_version=policy_version,
            defaults={
                "score": round(min(max(similarity, 0.0), 1.0), 4),
                "runner_up_margin": round(min(max(margin, 0.0), 1.0), 4),
                "status": MatchCandidate.Status.PENDING,
                "hard_conflicts": conflicts,
            },
        )
        if not created:
            return None
        MatchEvidence.objects.create(
            candidate=candidate,
            evidence_type="title_similarity",
            value={
                "provider_pair": provider_pair,
                "source_text": source_text,
                "target_text": target_text,
                "similarity": round(similarity, 4),
            },
            weight=round(min(max(similarity, 0.0), 1.0), 4),
        )
        MatchEvidence.objects.create(
            candidate=candidate,
            evidence_type="work_attributes",
            value={
                "provider_pair": provider_pair,
                # Which candidate side each set of attributes belongs to: the
                # candidate stores the pair in id order, and the evaluator needs
                # to know which provider it is looking at.
                "source_entity_id": source_entity_id,
                "target_entity_id": target_entity_id,
                "source": source_attributes,
                "target": target_attributes,
                "comparison": comparison,
            },
            weight=1,
        )
        return str(candidate.pk)

    @staticmethod
    def _policy_version(source_provider: str, target_provider: str) -> str:
        # Every pair now carries structured attributes, so all of them move to
        # the new version together; keeping the old key would leave the pairs
        # that already exist without evidence and out of the evaluator's reach.
        del source_provider, target_provider
        return POLICY_VERSION


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


provider_candidate_service = ProviderCandidateService()
