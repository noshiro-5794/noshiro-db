import json

from django.core.management.base import BaseCommand

from apps.sync.services.match_apply import match_apply_service


class Command(BaseCommand):
    help = (
        "Apply conservative auto-bind for AI match proposals. Dry-run by "
        "default; pass --apply to bind eligible candidates."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=200,
            help="Maximum number of proposals processed.",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Bind eligible candidates instead of only reporting them.",
        )
        parser.add_argument(
            "--keep-pending",
            action="store_true",
            help=(
                "Leave ineligible proposals pending instead of abstaining them. "
                "The scheduled run uses this so an unattended pass cannot retire "
                "a pair it merely could not confirm."
            ),
        )

    def handle(self, *args, **options):
        result = match_apply_service.run(
            limit=options["limit"],
            apply=options["apply"],
            abstain_ineligible=not options["keep_pending"],
        )
        self.stdout.write(json.dumps(result, ensure_ascii=False, default=str, indent=2))
