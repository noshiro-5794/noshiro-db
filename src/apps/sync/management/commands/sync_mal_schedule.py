import json

from django.core.management.base import BaseCommand

from apps.sync.services.mal_schedule_service import mal_schedule_service


class Command(BaseCommand):
    help = "Fetch and persist the MAL/Jikan weekly schedule and current season."

    def add_arguments(self, parser):
        parser.add_argument(
            "--page-size",
            type=int,
            default=25,
            help="Maximum items per Jikan page (max 25).",
        )
        parser.add_argument(
            "--max-pages-per-weekday",
            type=int,
            default=20,
            help="Safety cap for pages fetched per weekday list.",
        )

    def handle(self, *args, **options):
        result = mal_schedule_service.sync(
            page_size=options["page_size"],
            max_pages_per_weekday=options["max_pages_per_weekday"],
        )
        self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
