import json

from django.core.management.base import BaseCommand

from apps.sync.services.mal_season_pipeline import mal_season_pipeline_service


class Command(BaseCommand):
    help = (
        "Run the MAL current-season pipeline: schedule fetch, saved-record "
        "import, official AniList reconciliation, and title candidates."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-schedule",
            action="store_true",
            help="Reuse already-persisted MAL schedule records.",
        )
        parser.add_argument(
            "--evaluate",
            action="store_true",
            help="Dispatch AI evaluation for newly created match candidates.",
        )
        parser.add_argument(
            "--max-items",
            type=int,
            default=None,
            help="Cap the number of MAL schedule records promoted to entities.",
        )

    def handle(self, *args, **options):
        result = mal_season_pipeline_service.run(
            sync_schedules=not options["no_schedule"],
            evaluate=options["evaluate"],
            max_items=options["max_items"],
        )
        self.stdout.write(json.dumps(result, ensure_ascii=False, default=str, indent=2))
