"""Undo merges that joined works from different eras.

Title matching cannot tell a remake from a duplicate: "SHAMAN KING" is both the
2001 series and the 2021 reboot, and a confident-looking candidate bound them
into one row. Every such merge is reversible, so this command finds the pairs
whose premieres are years apart and splits them back into separate works.

Dry-run is the default.
"""

import json

from django.core.management.base import BaseCommand

from apps.index.models import AnimeProfile, MatchDecision, MergeEvent
from apps.index.services import entity_resolution_service


class Command(BaseCommand):
    help = "Split merges that joined works whose premieres are years apart."

    def add_arguments(self, parser):
        parser.add_argument(
            "--min-year-gap",
            type=int,
            default=2,
            help="Only split when the premieres differ by at least this many years.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Maximum number of merges to report or split.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Split the merges instead of only reporting them.",
        )
        parser.add_argument(
            "--decided-by",
            default="",
            help="Only consider merges decided by this actor.",
        )

    def handle(self, *args, **options):
        gap = max(1, int(options["min_year_gap"]))
        limit = max(1, int(options["limit"]))
        apply = options["apply"]
        decided_by = options["decided_by"]

        years = dict(
            AnimeProfile.objects.filter(premiered_on__isnull=False).values_list(
                "work__entity_id", "premiered_on"
            )
        )
        decisions = MatchDecision.objects.filter(outcome="bind").select_related(
            "candidate"
        )
        if decided_by:
            decisions = decisions.filter(decided_by=decided_by)

        rows = []
        split = 0
        skipped = 0
        for decision in decisions.iterator(chunk_size=500):
            if len(rows) >= limit:
                break
            candidate = decision.candidate
            left_year = years.get(candidate.left_entity_id)
            right_year = years.get(candidate.right_entity_id)
            if left_year is None or right_year is None:
                continue
            difference = abs(left_year.year - right_year.year)
            if difference < gap:
                continue
            merge_event_id = (decision.decision_data or {}).get("merge_event_id")
            merge_event = (
                MergeEvent.objects.filter(pk=merge_event_id).first()
                if merge_event_id
                else None
            )
            if merge_event is None or merge_event.reversed_at is not None:
                skipped += 1
                continue
            row = {
                "decision_id": str(decision.pk),
                "merge_event_id": str(merge_event.pk),
                "gap_years": difference,
                "left_premiered": left_year.isoformat(),
                "right_premiered": right_year.isoformat(),
                "decided_by": decision.decided_by,
            }
            if apply:
                entity_resolution_service.split(
                    merge_event=merge_event,
                    reason=(
                        f"Premieres differ by {difference} years "
                        f"({left_year.isoformat()} vs {right_year.isoformat()}); "
                        "same title, different work."
                    ),
                )
                split += 1
            rows.append(row)

        self.stdout.write(
            json.dumps(
                {
                    "min_year_gap": gap,
                    "applied": apply,
                    "found": len(rows),
                    "split": split,
                    "skipped_already_reversed": skipped,
                    "rows": rows,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
