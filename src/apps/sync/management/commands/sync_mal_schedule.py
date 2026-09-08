import json

from django.core.management.base import BaseCommand

from apps.sync.services.mal_schedule_service import mal_schedule_service


class Command(BaseCommand):
    help = "Fetch and persist the official MAL current-season listing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=500,
            help="Maximum items per MAL season page (max 500).",
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=10,
            help="Safety cap for pages fetched per seasonal listing.",
        )

    def handle(self, *args, **options):
        result = mal_schedule_service.sync(
            limit=options["limit"],
            max_pages=options["max_pages"],
        )
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
