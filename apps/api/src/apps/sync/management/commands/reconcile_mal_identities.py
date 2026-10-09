import json

from django.core.management.base import BaseCommand

from apps.index.services import mal_identity_service


class Command(BaseCommand):
    help = (
        "Reconcile MAL works against AniList official ids and persist binding "
        "decisions without touching raw source records."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only report what an apply run would do.",
        )
        parser.add_argument(
            "--create-only",
            action="store_true",
            help="Create pending candidates but never bind automatically.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help=(
                "Examine at most this many MAL records in this run. The sweep "
                "commits per pair, so a bounded run is safe to repeat."
            ),
        )

    def handle(self, *args, **options):
        summary = mal_identity_service.reconcile_official_links(
            create=not options["dry_run"],
            apply=not options["dry_run"] and not options["create_only"],
            limit=options["limit"],
        )
        self.stdout.write(json.dumps(summary, ensure_ascii=False, indent=2))
