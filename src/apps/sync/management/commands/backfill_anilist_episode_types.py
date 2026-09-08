"""Backfill EP type facts for existing AniList schedule episodes."""

from django.core.management.base import BaseCommand

from apps.sync.services.episode_type_backfill_service import (
    backfill_anilist_episode_types,
)


class Command(BaseCommand):
    help = (
        "Record episode-type=EP facts for AniList episodes that were imported "
        "from airing schedules before the sync wrote the type fact."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist facts instead of reporting a dry run.",
        )

    def handle(self, *args, **options):
        summary = backfill_anilist_episode_types(apply=options["apply"])
        mode = "applied" if options["apply"] else "dry-run"
        self.stdout.write(
            f"[{mode}] episodes={summary['episodes']} "
            f"linkable={summary['linkable']} "
            f"unlinked={summary['unlinked']}"
        )
