"""Link provider names written without observations to their exposing observation."""

from __future__ import annotations

from uuid import UUID

from django.db.models import Q

from apps.index.models import (
    Appearance,
    Credit,
    Entity,
    EntityName,
    EntityRelation,
    EntityRelationEvidence,
    ProviderRecord,
)


def _selected_observation_ids(queryset):
    return list(
        queryset.filter(
            observation__isnull=False,
            observation__provider_record__status=ProviderRecord.Status.ACTIVE,
            observation__current_projections__isnull=False,
        )
        .order_by("-observation__observed_at", "observation_id")
        .values_list("observation_id", flat=True)
        .distinct()[:1]
    )


def _observation_for_entity(entity: Entity) -> UUID | None:
    if entity.kind == Entity.Kind.CONTRIBUTOR:
        candidate_ids = _selected_observation_ids(
            Credit.objects.filter(contributor__entity_id=entity.pk)
        )
    elif entity.kind == Entity.Kind.CHARACTER:
        candidate_ids = _selected_observation_ids(
            Appearance.objects.filter(character_entity_id=entity.pk)
        )
    elif entity.kind == Entity.Kind.WORK:
        candidate_ids = _selected_observation_ids(
            EntityRelationEvidence.objects.filter(relation__to_entity_id=entity.pk)
        )
        if not candidate_ids:
            candidate_ids = _observation_from_related_work(entity)
    else:
        candidate_ids = []

    return candidate_ids[0] if candidate_ids else None


def _observation_from_related_work(entity: Entity) -> list[UUID]:
    relation = (
        EntityRelation.objects.filter(
            Q(from_entity_id=entity.pk) | Q(to_entity_id=entity.pk)
        )
        .select_related("from_entity", "to_entity")
        .first()
    )
    if relation is None:
        return []

    counterpart = (
        relation.to_entity
        if relation.from_entity_id == entity.pk
        else relation.from_entity
    )
    return list(
        EntityName.objects.filter(
            entity=counterpart,
            observation__isnull=False,
            observation__provider_record__status=ProviderRecord.Status.ACTIVE,
            observation__current_projections__isnull=False,
        )
        .order_by("-observation__observed_at", "observation_id")
        .values_list("observation_id", flat=True)
        .distinct()[:1]
    )


def backfill_orphan_entity_name_observations(*, apply: bool = False) -> dict[str, int]:
    orphan_names = EntityName.objects.filter(
        provider_record__isnull=False,
        observation__isnull=True,
    ).select_related("entity")
    total = orphan_names.count()
    linked = 0

    for name in orphan_names.iterator(chunk_size=500):
        observation_id = _observation_for_entity(name.entity)
        if observation_id is None:
            continue
        linked += 1
        if apply:
            EntityName.objects.filter(pk=name.pk, observation__isnull=True).update(
                observation_id=observation_id
            )

    return {"orphan_names": total, "linkable": linked, "unlinked": total - linked}
