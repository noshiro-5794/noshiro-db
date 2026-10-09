import json

from django.core.management.base import BaseCommand

from apps.ai.services import schedule_completion_service


class Command(BaseCommand):
    help = (
        "Run bounded AI/web schedule completion for tentative board slots "
        "and optionally apply accepted results to the board projection."
    )

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run research and create claims but do not update the board.",
        )

    def handle(self, *args, **options):
        summary = schedule_completion_service.run(
            limit=options["limit"],
            apply=not options["dry_run"],
        )
        self.stdout.write(
            json.dumps(summary, ensure_ascii=False, default=str, indent=2)
        )
