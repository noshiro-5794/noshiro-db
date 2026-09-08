import json

from django.core.management.base import BaseCommand

from apps.sync.services.schedule_coverage_service import schedule_coverage_service


class Command(BaseCommand):
    help = "Print current seasonal schedule coverage across all providers."

    def handle(self, *args, **options):
        self.stdout.write(
            json.dumps(schedule_coverage_service.report(), ensure_ascii=False, indent=2)
        )
