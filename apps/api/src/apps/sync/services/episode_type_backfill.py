"""Backfill EP type facts for AniList episodes imported from airing schedules."""

from __future__ import annotations

from django.db.models import QuerySet

from apps.index.models import Entity, Fact, Predicate
from apps.index.services import knowledge_ingestion_service

_EPISODE_TYPE_PREDICATE = "episode-type"
_EPISODE_NUMBER_PREDICATE = "episode-number"
_EPISODE_TYPE_VALUE = "EP"


def _missing_type_episode_entities() -> QuerySet:
    number_predicate = Predicate.objects.filter(slug=_EPISODE_NUMBER_PREDICATE).first()
    type_predicate = Predicate.objects.filter(slug=_EPISODE_TYPE_PREDICATE).first()
    if number_predicate is None:
        return Entity.objects.none()

    entities_with_type = Entity.objects.none()
    if type_predicate is not None:
        entities_with_type = Fact.objects.filter(predicate=type_predicate).values(
            "entity_id"
        )

    return (
        Fact.objects.filter(predicate=number_predicate)
        .exclude(entity_id__in=entities_with_type)
        .values("entity_id")
        .distinct()
    )


def backfill_anilist_episode_types(*, apply: bool = False) -> dict[str, int]:
    candidates = list(_missing_type_episode_entities())
    total = len(candidates)
    linked = 0

    for row in candidates:
        entity = Entity.objects.filter(
            pk=row["entity_id"],
            kind=Entity.Kind.EPISODE,
            provider_representations__provider_record__namespace__provider__slug="anilist",
        ).first()
        if entity is None:
            continue
        representation = (
            entity.provider_representations.filter(is_active=True)
            .select_related("provider_record")
            .first()
        )
        if representation is None:
            continue
        current = (
            representation.provider_record.current_observations.filter(
                schema_name="index.episode"
            )
            .select_related("observation")
            .order_by("-created_at")
            .first()
        )
        if current is None:
            continue
        linked += 1
        if apply:
            knowledge_ingestion_service.record_fact(
                entity=entity,
                observation=current.observation,
                slug=_EPISODE_TYPE_PREDICATE,
                name="Episode Type",
                value=_EPISODE_TYPE_VALUE,
                value_type="string",
                json_pointer="/episode/type",
            )

    return {"episodes": total, "linkable": linked, "unlinked": total - linked}
