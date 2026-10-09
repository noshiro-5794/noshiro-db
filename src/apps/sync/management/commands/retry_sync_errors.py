"""Retry the failures recorded in the sync ledger, then clean it up.

``SyncError`` is an audit ledger: tasks record every entity that failed, but
nothing reads it back, so a failure only clears when the incremental cursor
happens to pass that id again. This command retries the entities we can reach
directly and prunes the entries that are stale or that only belong to a whole
run (a calendar refresh or a retired full sync).
"""

from __future__ import annotations

from datetime import date, datetime, time

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.sync.models import SyncError
from apps.sync.services.incremental_sync import IncrementalSyncService


class Command(BaseCommand):
    help = "Retry entities recorded in SyncError and prune the ledger."

    def add_arguments(self, parser):
        parser.add_argument(
            "--task",
            type=str,
            help="Only touch this task's entries.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Retry at most this many entities.",
        )
        parser.add_argument(
            "--stale-before",
            type=str,
            help=(
                "Delete entries last seen before this date (YYYY-MM-DD) instead "
                "of retrying them."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would happen without changing anything.",
        )

    def handle(self, *args, **options):
        queryset = SyncError.objects.all()
        if options.get("task"):
            queryset = queryset.filter(task_name=options["task"])

        stale_before = self._parse_date(options.get("stale_before"))
        pruned = 0
        if stale_before is not None:
            stale = queryset.filter(last_occurred_at__lt=stale_before)
            pruned = stale.count()
            if not options["dry_run"]:
                stale.delete()
            queryset = queryset.filter(last_occurred_at__gte=stale_before)

        rows = list(queryset.order_by("last_occurred_at"))
        if options.get("limit"):
            rows = rows[: max(1, int(options["limit"]))]

        retryable: dict[str, list[SyncError]] = {}
        unretryable: dict[str, int] = {}
        for row in rows:
            if row.task_name in IncrementalSyncService.TASKS:
                retryable.setdefault(row.task_name, []).append(row)
            else:
                unretryable[row.task_name] = unretryable.get(row.task_name, 0) + 1

        synced = skipped = failed = 0
        for task_name, entries in retryable.items():
            config = IncrementalSyncService.TASKS[task_name]
            for entry in entries:
                if options["dry_run"]:
                    continue
                outcome = IncrementalSyncService._sync_one(
                    config=config, bangumi_id=entry.entity_id
                )
                if outcome == "failed":
                    failed += 1
                    SyncError.objects.filter(pk=entry.pk).update(
                        retry_count=entry.retry_count + 1,
                        last_occurred_at=timezone.now(),
                    )
                    continue
                SyncError.objects.filter(pk=entry.pk).delete()
                if outcome == "synced":
                    synced += 1
                else:
                    skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                "retry_sync_errors: "
                f"pruned {pruned}, synced {synced}, skipped {skipped}, "
                f"failed {failed}, unretryable {sum(unretryable.values())}"
            )
        )
        if unretryable:
            detail = ", ".join(
                f"{name} {count}" for name, count in sorted(unretryable.items())
            )
            self.stdout.write(f"  unretryable task names: {detail}")
        if options["dry_run"]:
            self.stdout.write("  dry run: nothing was changed")

    @staticmethod
    def _parse_date(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = date.fromisoformat(value)
        except ValueError as exc:
            raise CommandError("--stale-before must be a YYYY-MM-DD date.") from exc
        return timezone.make_aware(datetime.combine(parsed, time.min))
