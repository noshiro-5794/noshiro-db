"""Deterministic MAL identity reconciliation against official AniList ids."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction

from apps.index.models import (
    Entity,
    Fact,
    MatchCandidate,
    MatchDecision,
    MatchEvidence,
    ProviderRecord,
    ProviderRepresentation,
    Work,
)
from apps.index.services.resolution import (
    EntityResolutionError,
    entity_resolution_service,
)
from apps.sync.providers.mal import MAL_ANIME_NAMESPACE


class MALIdentityService:
    """Bind MAL records to canonical works using AniList's ``idMal`` fact."""

    OFFICIAL_POLICY = "official-mal-anilist-id-v1"
    ANILIST_ID_MAL_PREDICATE = "anilist-id-mal"

    @transaction.atomic
    def reconcile_official_links(
        self,
        *,
        create: bool = True,
        apply: bool = True,
    ) -> dict[str, Any]:
        summary = {
            "mal_entities": 0,
            "anilist_matches": 0,
            "candidates_created": 0,
            "candidates_existing": 0,
            "bound": 0,
            "abstained": 0,
            "skipped_redirected": 0,
        }
        mal_rows = (
            ProviderRepresentation.objects.filter(
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
        )
        for representation in mal_rows:
            mal_entity = entity_resolution_service.resolve(representation.entity)
            if mal_entity.id != representation.entity_id:
                # Already redirected into a canonical work; the MAL record is
                # represented on the root, so a fresh pair would be redundant.
                summary["skipped_redirected"] += 1
                continue
            summary["mal_entities"] += 1
            mal_id = int(representation.provider_record.external_id)
            for anilist_entity in self._anilist_entities_for_mal_id(mal_id):
                summary["anilist_matches"] += 1
                root = entity_resolution_service.resolve(anilist_entity)
                if root.id == mal_entity.id:
                    summary["skipped_redirected"] += 1
                    continue
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
                    entity_resolution_service.decide_candidate(
                        candidate=candidate,
                        outcome=outcome,
                        decided_by="official_mal_id",
                        reason=(
                            f"AniList explicitly references MAL {mal_id} "
                            "for the same anime."
                            if outcome == MatchDecision.Outcome.BIND
                            else "Official MAL id conflicts with entity granularity."
                        ),
                    )
                except EntityResolutionError:
                    entity_resolution_service.decide_candidate(
                        candidate=candidate,
                        outcome=MatchDecision.Outcome.ABSTAIN,
                        decided_by="official_mal_id",
                        reason="Official MAL id could not be bound safely.",
                    )
                    summary["abstained"] += 1
                    continue
                if outcome == MatchDecision.Outcome.BIND:
                    summary["bound"] += 1
                else:
                    summary["abstained"] += 1
        return summary

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
            return MatchDecision.Outcome.ABSTAIN
        types = set(
            Work.objects.filter(
                entity_id__in=(left_entity.pk, right_entity.pk)
            ).values_list("work_type", flat=True)
        )
        return (
            MatchDecision.Outcome.BIND
            if types <= {Work.WorkType.ANIME}
            else MatchDecision.Outcome.ABSTAIN
        )


mal_identity_service = MALIdentityService()
