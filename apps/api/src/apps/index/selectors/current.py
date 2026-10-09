from django.db.models import F, Q, QuerySet
from django.utils import timezone

from apps.index.models import (
    AiringBoard,
    AiringEvent,
    Appearance,
    ContentRating,
    Credit,
    EntityDescription,
    EntityMedia,
    EntityName,
    EntityRelation,
    EntityRelationEvidence,
    EntityTerm,
    ExternalLink,
    Fact,
    ProviderRecord,
    ReleaseWork,
    ReleaseWorkEvidence,
    VoicePerformance,
    Work,
)


def selected_observation_support(prefix: str = "observation") -> Q:
    """Match rows supported by the observation selected for its mapper output."""
    field = f"{prefix}__" if prefix else ""
    provider_record = f"{field}provider_record"
    return ~Q(
        **{
            f"{provider_record}__namespace__provider__redistribution_policy": (
                "forbidden"
            )
        }
    ) & Q(
        **{
            f"{field}isnull": False,
            f"{provider_record}__status": ProviderRecord.Status.ACTIVE,
            f"{field}current_projections__isnull": False,
            f"{field}current_projections__provider_record_id": F(
                f"{provider_record}__id"
            ),
        }
    )


def current_observation_support(prefix: str = "observation") -> Q:
    """Match source-independent rows or evidence selected by the mapper cursor."""
    field = f"{prefix}__" if prefix else ""
    return Q(**{f"{field}isnull": True}) | selected_observation_support(prefix)


def current_entity_names() -> QuerySet[EntityName]:
    return EntityName.objects.filter(
        Q(observation__isnull=True, provider_record__isnull=True)
        | selected_observation_support()
    ).distinct()


def current_entity_descriptions() -> QuerySet[EntityDescription]:
    return EntityDescription.objects.filter(
        Q(observation__isnull=True, provider_record__isnull=True)
        | selected_observation_support()
    ).distinct()


def current_entity_media() -> QuerySet[EntityMedia]:
    return EntityMedia.objects.filter(
        Q(observation__isnull=True, asset__provider_record__isnull=True)
        | selected_observation_support()
    ).distinct()


def current_external_links() -> QuerySet[ExternalLink]:
    return ExternalLink.objects.filter(
        Q(observation__isnull=True, provider_record__isnull=True)
        | selected_observation_support()
    ).distinct()


def current_content_ratings() -> QuerySet[ContentRating]:
    return ContentRating.objects.filter(selected_observation_support()).distinct()


def current_facts() -> QuerySet[Fact]:
    return (
        Fact.objects.filter(
            Q(evidence__isnull=True)
            | current_observation_support("evidence__observation")
        )
        .exclude(status=Fact.Status.REJECTED)
        .distinct()
    )


def current_airing_events() -> QuerySet[AiringEvent]:
    return AiringEvent.objects.filter(current_observation_support()).distinct()


def active_airing_board_events() -> QuerySet[AiringEvent]:
    """Return the weekday rows owned by the single active on-air board.

    The active board is the source of truth for the home calendar; precise
    per-episode airings from other observations belong to range queries and
    must never leak stale past episodes into the current-week board.
    """
    board = (
        AiringBoard.objects.filter(status=AiringBoard.Status.ACTIVE)
        .select_related("observation")
        .first()
    )
    if board is not None and board.observation_id is not None:
        return (
            AiringEvent.objects.filter(
                observation_id=board.observation_id,
                precision=AiringEvent.Precision.WEEKDAY,
            )
            .select_related(
                "work__entity",
                "episode_entity",
                "observation__provider_record__namespace__provider",
                "observation__mapping_run",
            )
            .order_by("weekday", "-collection_doing", "id")
        )
    # Tests and pre-AiringBoard environments fall back to the current
    # projection's weekday rows so the calendar never goes empty.
    return (
        current_airing_events()
        .filter(precision=AiringEvent.Precision.WEEKDAY)
        .order_by("weekday", "-collection_doing", "id")
    )


def supplementary_current_airing_events() -> QuerySet[AiringEvent]:
    """Return current AniList schedule rows not owned by the Bangumi board.

    The active board is refreshed from the Bangumi weekly calendar. Continuing
    works that only have AniList airing schedules must still surface once on
    the range-less calendar; each returned minute row is collapsed per work and
    weekday by the endpoint view.
    """
    return (
        current_airing_events()
        .filter(
            precision=AiringEvent.Precision.MINUTE,
            starts_at__gte=timezone.now(),
            work__work_type=Work.WorkType.ANIME,
            observation__provider_record__namespace__provider__slug="anilist",
            observation__provider_record__namespace__slug="calendar",
        )
        .select_related(
            "work__entity",
            "episode_entity",
            "observation__provider_record__namespace__provider",
            "observation__mapping_run",
        )
        .order_by("starts_at", "id")
    )


def current_entity_relations() -> QuerySet[EntityRelation]:
    return EntityRelation.objects.filter(
        Q(evidence__isnull=True) | current_observation_support("evidence__observation")
    ).distinct()


def current_entity_relation_evidence() -> QuerySet[EntityRelationEvidence]:
    return EntityRelationEvidence.objects.filter(
        selected_observation_support()
    ).distinct()


def current_credits() -> QuerySet[Credit]:
    return Credit.objects.filter(current_observation_support()).distinct()


def current_appearances() -> QuerySet[Appearance]:
    return Appearance.objects.filter(current_observation_support()).distinct()


def current_voice_performances() -> QuerySet[VoicePerformance]:
    return VoicePerformance.objects.filter(
        current_observation_support()
        & current_observation_support("appearance__observation")
    ).distinct()


def current_entity_terms() -> QuerySet[EntityTerm]:
    return EntityTerm.objects.filter(current_observation_support()).distinct()


def current_release_work_links() -> QuerySet[ReleaseWork]:
    return ReleaseWork.objects.filter(
        Q(evidence__isnull=True) | current_observation_support("evidence__observation")
    ).distinct()


def current_release_work_evidence() -> QuerySet[ReleaseWorkEvidence]:
    return ReleaseWorkEvidence.objects.filter(selected_observation_support()).distinct()
