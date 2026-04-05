from django.core.management.base import BaseCommand

from sync.tasks.scheduler import SyncScheduler


class Command(BaseCommand):
    help = "Run full sync scheduler"

    def handle(self, *args, **options):
        scheduler = SyncScheduler()
        scheduler.run_all()
