"""Deterministic MAL identity reconciliation against official AniList ids."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from apps.index.models import (
    CandidateDecision,
    Entity,
    EntityRepresentation,
    Fact,
    MatchCandidate,
    MatchEvidence,
    ProviderRecord,
    Work,
)
from apps.index.services.resolution import (
    EntityResolutionError,
    entity_resolution_service,
)
from apps.sync.providers.mal import MAL_ANIME_NAMESPACE

# Rows fetched per database round trip while walking MAL representations.
WALK_CHUNK_SIZE = 500


class MALIdentityService:
    """Bind MAL records to canonical works using AniList's ``idMal`` fact."""

    OFFICIAL_POLICY = "official-mal-anilist-id-v1"
    ANILIST_ID_MAL_PREDICATE = "anilist-id-mal"

    def reconcile_official_links(
        self,
        *,
        create: bool = True,
        apply: bool = True,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Bind MAL works to their AniList twin using AniList's official id.

        Every pair commits on its own. An earlier version wrapped the whole
        sweep in a single transaction, which meant a run of thirty thousand
        pairs held locks for the entire pass, hid its progress from every other
        connection, and rolled the lot back if the last pair failed or the task
        hit its time limit — the daily season task did exactly that and had been
        merging nothing for weeks.

        ``limit`` bounds the records examined for binding, not the rows walked
        past: the ordering restarts at the first MAL id on every run, so a
        representation that already resolves to a canonical work can never bind
        and must not spend the batch. Letting those rows consume it pinned every
        daily run to the handful of bindable records near the top of the
        ordering and left the rest of the catalogue unexamined.
        """
        summary = {
            "mal_entities": 0,
            "examined": 0,
            "anilist_matches": 0,
            "candidates_created": 0,
            "candidates_existing": 0,
            "bound": 0,
            "abstained": 0,
            "skipped_redirected": 0,
        }
        # One query loads the whole redirect graph, so a row that no longer
        # resolves to itself costs a dict lookup instead of a query per hop. The
        # walk still visits those rows rather than excluding them in SQL: the
        # summary reports how many merged records it stepped over, and rows this
        # very run redirects are only visible in the map it keeps updating.
        redirects = entity_resolution_service.redirect_map()
        root_entities: dict[Any, Entity] = {}
        mal_rows = (
            EntityRepresentation.objects.filter(
                is_active=True,
                provider_record__namespace__provider__slug=(
                    MAL_ANIME_NAMESPACE.source.slug
                ),
                provider_record__namespace__slug=MAL_ANIME_NAMESPACE.slug,
                provider_record__status=ProviderRecord.Status.ACTIVE,
                entity__lifecycle=Entity.Lifecycle.ACTIVE,
            )
            .select_related("entity", "provider_record")
            .order_by("provider_record__external_id")
            # The MAL table outgrows a batch by orders of magnitude, so it is
            # streamed rather than materialized; a bounded run stops at its
            # budget without holding every row in memory.
            .iterator(chunk_size=WALK_CHUNK_SIZE)
        )
        for representation in mal_rows:
            if limit is not None and summary["examined"] >= limit:
                break
            mal_entity = representation.entity
            if (
                entity_resolution_service.resolve_with(redirects, mal_entity.pk)
                != mal_entity.pk
            ):
                # Already redirected into a canonical work, so the MAL record is
                # represented on the root and a fresh pair would be redundant.
                # Skipping it costs no budget and no query.
                summary["skipped_redirected"] += 1
                continue
            summary["mal_entities"] += 1
            summary["examined"] += 1
            mal_id = int(representation.provider_record.external_id)
            for anilist_entity in self._anilist_entities_for_mal_id(mal_id):
                summary["anilist_matches"] += 1
                root_id = entity_resolution_service.resolve_with(
                    redirects, anilist_entity.pk
                )
                if root_id == mal_entity.pk:
                    summary["skipped_redirected"] += 1
                    continue
                root = root_entities.get(root_id)
                if root is None:
                    root = (
                        anilist_entity
                        if root_id == anilist_entity.pk
                        else Entity.objects.get(pk=root_id)
                    )
                    root_entities[root_id] = root
                candidate, created = self._ensure_candidate(
                    left_entity=mal_entity,
                    right_entity=root,
                    mal_id=mal_id,
                    create=create,
                )
                if candidate is None:
                    continue
                summary["candidates_created" if created else "candidates_existing"] += 1
                if candidate.status != MatchCandidate.Status.PENDING:
                    continue
                outcome = self._outcome_for_pair(mal_entity, root)
                if not apply:
                    continue
                try:
                    decision = entity_resolution_service.decide_candidate(
                        candidate=candidate,
                        outcome=outcome,
                        decided_by="official_mal_id",
                        reason=(
                            f"AniList explicitly references MAL {mal_id} "
                            "for the same anime."
                            if outcome == CandidateDecision.Outcome.BIND
                            else "Official MAL id conflicts with entity granularity."
                        ),
                    )
                except EntityResolutionError:
                    entity_resolution_service.decide_candidate(
                        candidate=candidate,
                        outcome=CandidateDecision.Outcome.ABSTAIN,
                        decided_by="official_mal_id",
                        reason="Official MAL id could not be bound safely.",
                    )
                    summary["abstained"] += 1
                    continue
                if outcome == CandidateDecision.Outcome.BIND:
                    summary["bound"] += 1
                    self._follow_own_merge(redirects=redirects, decision=decision)
                else:
                    summary["abstained"] += 1
        return summary

    @staticmethod
    def _follow_own_merge(*, redirects: dict, decision: CandidateDecision) -> None:
        """Record a merge this sweep just made in its own redirect snapshot.

        Pairs commit as they are decided, so the graph loaded at the start of
        the sweep is already stale for the pairs it bound itself. Following the
        new redirect keeps a later representation of the merged entity from
        being examined again as if it were still canonical.
        """
        source_id = decision.decision_data.get("source_entity_id")
        target_id = decision.decision_data.get("canonical_entity_id")
        if source_id and target_id:
            redirects[UUID(source_id)] = UUID(target_id)

    @staticmethod
    def _anilist_entities_for_mal_id(mal_id: int) -> list[Entity]:
        ids = (
            Fact.objects.filter(
                predicate__slug=MALIdentityService.ANILIST_ID_MAL_PREDICATE,
                value=mal_id,
                entity__kind=Entity.Kind.WORK,
                entity__lifecycle=Entity.Lifecycle.ACTIVE,
            )
            .values_list("entity_id", flat=True)
            .distinct()
        )
        return list(Entity.objects.filter(pk__in=ids).order_by("created_at"))

    @staticmethod
    def _ensure_candidate(
        *,
        left_entity: Entity,
        right_entity: Entity,
        mal_id: int,
        create: bool,
    ) -> tuple[MatchCandidate | None, bool]:
        left, right = sorted((left_entity, right_entity), key=lambda item: str(item.pk))
        candidate = (
            MatchCandidate.objects.filter(
                left_entity=left,
                right_entity=right,
                policy_version=MALIdentityService.OFFICIAL_POLICY,
            )
            .select_related("left_entity", "right_entity")
            .first()
        )
        if candidate is not None:
            return candidate, False
        if not create:
            return None, False
        candidate = MatchCandidate.objects.create(
            left_entity=left,
            right_entity=right,
            score=Decimal("1.0000"),
            runner_up_margin=Decimal("1.0000"),
            policy_version=MALIdentityService.OFFICIAL_POLICY,
            status=MatchCandidate.Status.PENDING,
        )
        MatchEvidence.objects.create(
            candidate=candidate,
            evidence_type="official_external_id",
            value={
                "provider_pair": "mal:anilist",
                "external_id": mal_id,
            },
            weight=Decimal("1.0000"),
        )
        return candidate, True

    @staticmethod
    def _outcome_for_pair(left_entity: Entity, right_entity: Entity) -> str:
        if (
            left_entity.kind != Entity.Kind.WORK
            or right_entity.kind != Entity.Kind.WORK
        ):
            return CandidateDecision.Outcome.ABSTAIN
        types = set(
            Work.objects.filter(
                entity_id__in=(left_entity.pk, right_entity.pk)
            ).values_list("work_type", flat=True)
        )
        if types - {Work.WorkType.ANIME}:
            return CandidateDecision.Outcome.ABSTAIN
        if MALIdentityService._premieres_conflict(left_entity, right_entity):
            # AniList's idMal is authoritative about identity, but the same title
            # a generation apart is a remake: either the mapping or one side's
            # date is wrong, and silently collapsing the two rewrites history.
            return CandidateDecision.Outcome.ABSTAIN
        return CandidateDecision.Outcome.BIND

    @staticmethod
    def _premieres_conflict(left_entity: Entity, right_entity: Entity) -> bool:
        from apps.index.models import AnimeProfile

        years = list(
            AnimeProfile.objects.filter(
                work__entity_id__in=(left_entity.pk, right_entity.pk),
                premiered_on__isnull=False,
            ).values_list("premiered_on", flat=True)
        )
        if len(years) < 2:
            return False
        return abs(years[0].year - years[1].year) > 1


mal_identity_service = MALIdentityService()
