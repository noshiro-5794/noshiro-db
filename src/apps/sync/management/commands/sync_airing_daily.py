import json

from django.core.management.base import BaseCommand

from apps.sync.models import SyncJob
from apps.sync.services.airing_daily_sync_service import airing_daily_sync_service
from apps.sync.services.sync_job_service import sync_job_service


class Command(BaseCommand):
    help = "Refresh subjects and episodes for the current on-air board"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            help="Override the configured daily batch size.",
        )
        parser.add_argument(
            "--status",
            action="store_true",
            help="Print today's airing daily queue state without running.",
        )
        parser.add_argument(
            "--no-job",
            action="store_true",
            help="Run without persisting a SyncJob.",
        )

    def handle(self, *args, **options):
        if options["status"]:
            result = airing_daily_sync_service.get_status()
        else:
            job = None
            if not options["no_job"]:
                job = sync_job_service.create_job(
                    job_type=SyncJob.JobType.AIRING_DAILY,
                    parameters={
                        "batch_size": options.get("batch_size"),
                        "source": "management-command",
                    },
                )
            result = airing_daily_sync_service.sync_day(
                batch_size=options.get("batch_size"),
                job_id=str(job.id) if job is not None else None,
                verbose=True,
            )

        self.stdout.write(json.dumps(result, ensure_ascii=False, default=str, indent=2))
