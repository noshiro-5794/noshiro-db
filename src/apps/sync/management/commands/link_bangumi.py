import json

from django.core.management.base import BaseCommand

from apps.sync.services.bangumi_link_service import bangumi_link_service


class Command(BaseCommand):
    help = (
        "Resolve MAL-anchored works that lack a Bangumi link: search Bangumi, "
        "let AI pick the high-confidence subject, sync it by id, and link."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of works processed in this run.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Bind accepted candidates instead of leaving them pending.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-run works that already have a no-match or failed attempt.",
        )

    def handle(self, *args, **options):
        result = bangumi_link_service.run_missing(
            limit=options["limit"],
            apply=options["apply"],
            force=options["force"],
        )
        self.stdout.write(json.dumps(result, ensure_ascii=False, default=str, indent=2))
