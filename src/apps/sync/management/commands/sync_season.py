import json

from django.core.management.base import BaseCommand

from apps.sync.services.season_pipeline_service import season_pipeline_service


class Command(BaseCommand):
    help = (
        "Sync the current season from AniList and MAL, promote entities, "
        "reconcile official ids, generate title candidates, and rebuild board."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-items-per-source",
            type=int,
            default=None,
            help="Cap saved record promotion per source.",
        )
        parser.add_argument(
            "--evaluate",
            action="store_true",
            help="Dispatch AI evaluation for newly created candidates.",
        )

    def handle(self, *args, **options):
        result = season_pipeline_service.run(
            max_items_per_source=options["max_items_per_source"],
            evaluate=options["evaluate"],
        )
        self.stdout.write(json.dumps(result, ensure_ascii=False, default=str, indent=2))
