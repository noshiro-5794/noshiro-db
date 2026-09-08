import json

from django.core.management.base import BaseCommand

from apps.sync.services.mal_link_recall_service import mal_link_recall_service


class Command(BaseCommand):
    help = (
        "Recall missing MAL candidates for unresolved Bangumi board works: "
        "an agent searches the internal graph and official MAL API, then "
        "creates high-confidence pending candidates."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of unresolved works processed in this run.",
        )
        parser.add_argument(
            "--no-evaluate",
            action="store_true",
            help="Create candidates without dispatching the adjudicator.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-run works that already have a completed recall attempt.",
        )

    def handle(self, *args, **options):
        result = mal_link_recall_service.run_missing(
            limit=options["limit"],
            evaluate=not options["no_evaluate"],
            force=options["force"],
        )
        self.stdout.write(json.dumps(result, ensure_ascii=False, default=str, indent=2))
