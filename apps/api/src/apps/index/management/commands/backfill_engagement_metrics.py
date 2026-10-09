"""Copy MAL and AniList engagement numbers into the metric time series.

Those two importers originally recorded reach as facts, while VNDB and Bangumi
recorded it as ``MetricSnapshot`` rows. The popularity ranking reads the single
metric store, so this one-off command re-projects the already-stored facts
instead of re-fetching every record from the providers.
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.management.base import BaseCommand

from apps.index.models import FactEvidence, MetricSnapshot

FACT_TO_METRIC = {
    "mal-members": "members",
    "anilist-popularity": "popularity",
    "anilist-favourites": "favourites",
    "anilist-trending": "trending",
}


class Command(BaseCommand):
    help = "Backfill MetricSnapshot rows from already-imported MAL/AniList facts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=2000,
            help="How many metric rows to insert per transaction.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        batch_size = max(1, int(options["batch_size"]))
        rows = (
            FactEvidence.objects.filter(
                fact__predicate__slug__in=FACT_TO_METRIC,
            )
            .values_list(
                "fact__entity_id",
                "fact__predicate__slug",
                "fact__value",
                "observation__provider_record_id",
                "observation__observed_at",
            )
            .iterator()
        )
        created = 0
        skipped = 0
        pending: list[MetricSnapshot] = []
        seen: set[tuple] = set()
        for entity_id, slug, raw, provider_record_id, observed_at in rows:
            try:
                value = Decimal(str(raw))
            except (InvalidOperation, TypeError, ValueError):
                skipped += 1
                continue
            key = (provider_record_id, slug, observed_at)
            if key in seen:
                continue
            seen.add(key)
            pending.append(
                MetricSnapshot(
                    entity_id=entity_id,
                    provider_record_id=provider_record_id,
                    metric=FACT_TO_METRIC[slug],
                    value=value,
                    observed_at=observed_at,
                )
            )
            if len(pending) >= batch_size:
                created += self._flush(pending)
                pending = []
        created += self._flush(pending)
        self.stdout.write(
            self.style.SUCCESS(
                f"Backfilled {created} metric rows (skipped {skipped} unusable values)."
            )
        )

    @staticmethod
    def _flush(batch: list[MetricSnapshot]) -> int:
        if not batch:
            return 0
        MetricSnapshot.objects.bulk_create(batch, ignore_conflicts=True)
        return len(batch)
