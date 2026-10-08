"""Delete failed AI runs that nothing downstream depends on.

A provider outage writes one failed ``AIRun`` per attempted call — 8,770 rows
for a single afternoon of ``402 Payment Required`` — which drowns the telemetry
that still matters, such as a claim waiting on a policy decision.

A run is only deletable when no proposal cites it and it is not attached to an
agent step; anything else is left alone. Dry-run is the default.
"""

import json
from datetime import datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.ai.models import AIRun


class Command(BaseCommand):
    help = "Prune failed AI runs that no proposal or agent step refers to."

    def add_arguments(self, parser):
        parser.add_argument(
            "--use-case",
            type=str,
            default="",
            help="Only prune runs for this use case.",
        )
        parser.add_argument(
            "--before",
            type=str,
            default="",
            help="Only prune runs created before this date (YYYY-MM-DD).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Delete at most this many runs (zero deletes every match).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Delete the matching runs instead of only counting them.",
        )

    def handle(self, *args, **options):
        queryset = AIRun.objects.filter(
            status=AIRun.Status.FAILED,
            proposals__isnull=True,
            agent_step__isnull=True,
        )
        use_case = options["use_case"].strip()
        if use_case:
            queryset = queryset.filter(use_case=use_case)
        before = options["before"].strip()
        if before:
            try:
                cutoff = datetime.strptime(before, "%Y-%m-%d").date()
            except ValueError as exc:
                raise CommandError("--before must be YYYY-MM-DD.") from exc
            queryset = queryset.filter(
                created_at__lt=timezone.make_aware(
                    datetime.combine(cutoff, time.min), timezone.get_current_timezone()
                )
            )
        queryset = queryset.distinct()
        matching = queryset.count()
        deleted = 0
        if options["apply"]:
            limit = max(0, int(options["limit"]))
            ids = list(queryset.values_list("id", flat=True)[: limit or None])
            for start in range(0, len(ids), 500):
                batch = ids[start : start + 500]
                deleted += AIRun.objects.filter(pk__in=batch).delete()[0]
        self.stdout.write(
            json.dumps(
                {
                    "matching": matching,
                    "deleted": deleted,
                    "applied": bool(options["apply"]),
                },
                indent=2,
            )
        )
