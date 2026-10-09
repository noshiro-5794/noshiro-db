"""Rank every work by the engagement number of one authoritative source.

Reach is reported in units that cannot be compared across providers: MAL counts
list members, VNDB counts ratings, AniList counts list members, Bangumi counts
its own users. Averaging them produced a number that belonged to no source in
particular, so each catalogue type follows a single source instead:

* anime -> AniList ``popularity`` (users who keep it on their list)
* galgame -> VNDB rating count

Which source is authoritative is a coverage question, not a taste question. MAL
is the natural anime master, but it has never been full-synced, so it knows a
few hundred entries out of the whole anime catalogue. AniList is full-synced
and carries the same "how many people list it" number, so it ranks anime until
a MAL full sync makes the switch worthwhile — that switch is the one line in
``PRIMARY_SIGNALS`` below.

Other providers keep contributing facts and metrics; they simply do not
influence the ordering.

The raw number is never compared across sources, only inside its own series: it
is turned into a percentile, so the score is a 0-100 standing within the
source's own population. The API never exposes it — it only decides the order a
visitor sees.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.index.models import Entity, MetricSnapshot, Work
from apps.index.services.resolution import entity_resolution_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PrimarySignal:
    """The one source whose number ranks a catalogue type."""

    work_type: str
    source: str
    metric: str


PRIMARY_SIGNALS: tuple[PrimarySignal, ...] = (
    PrimarySignal(Work.WorkType.ANIME, "anilist", "popularity"),
    PrimarySignal(Work.WorkType.GALGAME, "vndb", "votes"),
)

SCORE_SCALE = Decimal("100")


class PopularityService:
    """Rebuild ``Work.popularity`` from each type's primary source."""

    def refresh(self, *, now=None) -> int:
        """Recompute every work's popularity and return how many were scored.

        The whole table is rebuilt rather than incrementally patched: the score
        is a percentile, so one new record shifts the standing for everyone.
        """
        now = now or timezone.now()
        redirects = entity_resolution_service.redirect_map()
        scores: dict = {}
        for signal in PRIMARY_SIGNALS:
            scores.update(self._rank(signal, redirects))
        if not scores:
            logger.info("Popularity refresh found no primary engagement metrics.")
            return 0
        return self._persist(scores, now=now)

    @staticmethod
    def _rank(signal: PrimarySignal, redirects: dict) -> dict:
        """Percentile standing of each work inside its source's own series."""
        # ``entity__work__work_type`` restricts the series to the type this
        # source ranks, so a stray metric on the wrong kind of record cannot
        # move anyone's position.
        rows = (
            MetricSnapshot.objects.filter(
                metric=signal.metric,
                provider_record__namespace__provider__slug=signal.source,
                entity__work__work_type=signal.work_type,
            )
            .order_by("entity_id", "-observed_at")
            .distinct("entity_id")
            .values_list("entity_id", "value")
        )
        latest: dict = {}
        for entity_id, value in rows:
            root = entity_resolution_service.resolve_with(redirects, entity_id)
            current = latest.get(root)
            if current is None or value > current:
                latest[root] = value
        if not latest:
            return {}
        ordered = sorted(latest.items(), key=lambda item: (item[1], str(item[0])))
        denominator = len(ordered) - 1
        scores: dict = {}
        previous_value = None
        previous_rank = Decimal(0)
        for index, (entity_id, value) in enumerate(ordered):
            if value == previous_value:
                # Equal reach is an equal standing; sharing the lower rank keeps
                # the order stable instead of inventing a difference.
                rank = previous_rank
            elif denominator <= 0:
                rank = Decimal(1)
            else:
                rank = Decimal(index) / Decimal(denominator)
            previous_value, previous_rank = value, rank
            scores[entity_id] = rank * SCORE_SCALE
        return scores

    @transaction.atomic
    def _persist(self, scores: dict, *, now) -> int:
        if not scores:
            return 0
        scorable = set(
            Entity.objects.filter(
                pk__in=list(scores),
                lifecycle=Entity.Lifecycle.ACTIVE,
                visibility=Entity.Visibility.PUBLIC,
            ).values_list("pk", flat=True)
        )
        scored_ids = [entity_id for entity_id in scorable if entity_id in scores]
        works = list(Work.objects.filter(entity_id__in=scored_ids))
        for work in works:
            work.popularity = scores[work.entity_id].quantize(Decimal("0.000001"))
            work.popularity_refreshed_at = now
        Work.objects.bulk_update(
            works, ["popularity", "popularity_refreshed_at"], batch_size=1000
        )
        # Every scorable work already carries this run's timestamp, so a work
        # that lost its primary signal must not keep last round's score.
        Work.objects.filter(entity_id__in=scorable).exclude(
            entity_id__in=scored_ids
        ).update(popularity=0, popularity_refreshed_at=now)
        Work.objects.filter(popularity_refreshed_at__lt=now).update(
            popularity=0, popularity_refreshed_at=now
        )
        return len(works)


popularity_service = PopularityService()


__all__ = [
    "PRIMARY_SIGNALS",
    "PopularityService",
    "PrimarySignal",
    "popularity_service",
]
