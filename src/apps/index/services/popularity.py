"""Derive a single, provider-neutral popularity score for every work.

The catalogue has to order works by how much of an audience actually cares
about them, but the four providers report that in incompatible units: MAL
counts list members, VNDB and Bangumi count ratings, AniList reports reach and
recent activity. Comparing the raw numbers is meaningless — a niche visual
novel and a mainstream anime never share a scale.

So each engagement metric is first turned into a percentile rank inside its own
metric, then those ranks are combined with fixed weights. The result is a
0-100 score the API never exposes: it only decides the ordering a visitor sees.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.index.models import Entity, MetricSnapshot, Work
from apps.index.services.resolution import entity_resolution_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PopularitySignal:
    """One engagement metric and how much it should influence the score."""

    metric: str
    weight: Decimal


# Weights express "how many people care", not "how well it was received".
# Review scores and rank positions are deliberately absent: they measure
# reception, and mixing them with reach made a beloved niche title outrank a
# title with ten times the audience.
POPULARITY_SIGNALS: tuple[PopularitySignal, ...] = (
    PopularitySignal("members", Decimal("1.0")),
    PopularitySignal("votes", Decimal("0.9")),
    PopularitySignal("popularity", Decimal("0.7")),
    PopularitySignal("trending", Decimal("0.6")),
    PopularitySignal("scoring-users", Decimal("0.6")),
    PopularitySignal("favourites", Decimal("0.5")),
)

SCORE_SCALE = Decimal("100")


class PopularityService:
    """Rebuild ``Work.popularity`` from the metric time series."""

    def refresh(self, *, now=None) -> int:
        """Recompute every work's popularity and return how many were scored.

        The whole table is rebuilt rather than incrementally patched: the score
        is a percentile, so one new record shifts the scale for everyone.
        """
        now = now or timezone.now()
        metrics = tuple(signal.metric for signal in POPULARITY_SIGNALS)
        latest = self._latest_metrics(metrics)
        if not latest:
            logger.info("Popularity refresh found no engagement metrics.")
            return 0
        redirects = entity_resolution_service.redirect_map()
        canonical = self._collapse_to_canonical(latest, redirects)
        scores = self._score(canonical)
        return self._persist(scores, now=now)

    @staticmethod
    def _latest_metrics(metrics: tuple[str, ...]) -> dict[tuple, Decimal]:
        """Keep only the newest observation of each metric per entity."""
        rows = (
            MetricSnapshot.objects.filter(metric__in=metrics)
            .order_by("entity_id", "metric", "-observed_at")
            .distinct("entity_id", "metric")
            .values_list("entity_id", "metric", "value")
        )
        return {(entity_id, metric): value for entity_id, metric, value in rows}

    @staticmethod
    def _collapse_to_canonical(
        latest: dict[tuple, Decimal], redirects: dict
    ) -> dict[tuple, Decimal]:
        """Move merged entities' metrics onto the entity visitors land on."""
        canonical: dict[tuple, Decimal] = {}
        for (entity_id, metric), value in latest.items():
            root = entity_resolution_service.resolve_with(redirects, entity_id)
            key = (root, metric)
            current = canonical.get(key)
            if current is None or value > current:
                canonical[key] = value
        return canonical

    @staticmethod
    def _score(canonical: dict[tuple, Decimal]) -> dict:
        """Blend each entity's normalised signals into a 0-100 score."""
        by_metric: dict[str, list[tuple]] = defaultdict(list)
        for (entity_id, metric), value in canonical.items():
            by_metric[metric].append((value, entity_id))
        weights = {signal.metric: signal.weight for signal in POPULARITY_SIGNALS}
        totals: dict = defaultdict(Decimal)
        weight_sums: dict = defaultdict(Decimal)
        for metric, rows in by_metric.items():
            rows.sort()
            denominator = len(rows) - 1
            for index, (_, entity_id) in enumerate(rows):
                rank = (
                    Decimal(1)
                    if denominator <= 0
                    else Decimal(index) / Decimal(denominator)
                )
                weight = weights[metric]
                totals[entity_id] += weight * rank
                weight_sums[entity_id] += weight
        return {
            entity_id: (totals[entity_id] / weight_sums[entity_id] * SCORE_SCALE)
            for entity_id in totals
        }

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
        # that lost all of its signals must not keep last round's score.
        Work.objects.filter(entity_id__in=scorable).exclude(
            entity_id__in=scored_ids
        ).update(popularity=0, popularity_refreshed_at=now)
        Work.objects.filter(popularity_refreshed_at__lt=now).update(
            popularity=0, popularity_refreshed_at=now
        )
        return len(works)


popularity_service = PopularityService()


__all__ = [
    "POPULARITY_SIGNALS",
    "PopularityService",
    "PopularitySignal",
    "popularity_service",
]
