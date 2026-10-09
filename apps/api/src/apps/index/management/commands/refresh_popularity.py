from typing import Any

from django.core.management.base import BaseCommand

from apps.index.services import popularity_service


class Command(BaseCommand):
    help = "Rebuild the provider-neutral popularity ranking of every work."

    def handle(self, *args: Any, **options: Any) -> None:
        scored = popularity_service.refresh()
        self.stdout.write(
            self.style.SUCCESS(f"Popularity refreshed for {scored} works.")
        )
