import json

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.sync.services.subject_refresh import subject_refresh_service


class Command(BaseCommand):
    help = (
        "Refresh known Bangumi subjects, oldest first, promoting legacy rows "
        "onto the modern provider-record form."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help=(
                "How many subjects to re-fetch. Defaults to "
                "BANGUMI_SUBJECT_REFRESH_BATCH_SIZE."
            ),
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Include records that no visible catalogue work points at.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the selection without fetching anything.",
        )

    def handle(self, *args, **options):
        limit = options["limit"] or settings.BANGUMI_SUBJECT_REFRESH_BATCH_SIZE
        catalogue_only = not options["all"]
        if options["dry_run"]:
            targets = subject_refresh_service.select_targets(
                limit=limit, catalogue_only=catalogue_only
            )
            self.stdout.write(
                json.dumps(
                    {
                        "limit": limit,
                        "catalogue_only": catalogue_only,
                        "selected": len(targets),
                        "legacy": sum(
                            1 for record in targets if record.raw_state == "legacy"
                        ),
                        "sample": [record.external_id for record in targets[:10]],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        result = subject_refresh_service.refresh(
            limit=limit, catalogue_only=catalogue_only
        )
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
