import json

from django.core.management.base import BaseCommand

from apps.index.services import airing_board_projection_service


class Command(BaseCommand):
    help = (
        "Rebuild the curated multi-source airing board projection from "
        "provider schedule facts without touching raw observations."
    )

    def handle(self, *args, **options):
        summary = airing_board_projection_service.rebuild()
        self.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
