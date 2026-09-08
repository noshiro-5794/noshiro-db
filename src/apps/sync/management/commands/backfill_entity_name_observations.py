"""Backfill legacy AniList names missing an observation link."""

from django.core.management.base import BaseCommand

from apps.sync.services.entity_name_backfill_service import (
    backfill_orphan_entity_name_observations,
)


class Command(BaseCommand):
    help = (
        "Link provider EntityName rows that were written without an observation "
        "to the current observation that exposed the owning entity."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist observation links instead of reporting a dry run.",
        )

    def handle(self, *args, **options):
        summary = backfill_orphan_entity_name_observations(apply=options["apply"])
        mode = "applied" if options["apply"] else "dry-run"
        self.stdout.write(
            f"[{mode}] orphan_names={summary['orphan_names']} "
            f"linkable={summary['linkable']} unlinked={summary['unlinked']}"
        )
