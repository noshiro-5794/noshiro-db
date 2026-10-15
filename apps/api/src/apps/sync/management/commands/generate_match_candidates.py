"""Generate idempotent cross-provider work candidates.

The sweep is resumable: each run takes the next window of source works and
records where it stopped, so a command run is a slice of a pass rather than a
restart. Only works take part - anime against anime, VNDB visual novels against
Bangumi game entries - because those are the entities the catalogue projects.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.index.services import provider_candidate_service
from config.celery import app as celery_app

EVALUATE_TASK = "apps.ai.tasks.evaluate_match_candidate_task"

# Source provider, source namespace, and the target each one is matched toward.
LEGS = {
    "anilist": ("anilist", "anime", "bangumi", "subject"),
    "mal": ("mal", "anime", "bangumi", "subject"),
    "vndb": ("vndb", "vn", "bangumi", "subject"),
}


class Command(BaseCommand):
    help = (
        "Create cross-provider work candidates for a source provider. No entity "
        "is merged; AI evaluation is optional. The sweep continues from where the "
        "previous run stopped unless --reset-cursor is given."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=tuple(LEGS),
            default="anilist",
            help="Provider whose works are matched toward Bangumi.",
        )
        parser.add_argument(
            "--min-similarity",
            type=float,
            default=None,
            help=(
                "pg_trgm blocking threshold; defaults to "
                "MATCH_CANDIDATE_MIN_SIMILARITY."
            ),
        )
        parser.add_argument("--top-k", type=int, default=None)
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help=(
                "Source works examined in this run; defaults to "
                "MATCH_CANDIDATE_BATCH_SIZE."
            ),
        )
        parser.add_argument(
            "--reset-cursor",
            action="store_true",
            help="Start this sweep from the top of the catalogue.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report pairs without writing candidates or moving the cursor.",
        )
        parser.add_argument(
            "--evaluate",
            action="store_true",
            help="Dispatch AI evaluation for each newly created candidate.",
        )

    def handle(self, *args, **options):
        service = provider_candidate_service
        source_provider, source_namespace, target_provider, target_namespace = LEGS[
            options["source"]
        ]
        if options["reset_cursor"]:
            service.reset_cursor(
                shard=service.sweep_shard(
                    source_provider=source_provider,
                    source_namespace=source_namespace,
                    target_provider=target_provider,
                    target_namespace=target_namespace,
                )
            )
        kwargs = {
            "min_similarity": options["min_similarity"],
            "top_k": options["top_k"],
            "limit": options["limit"],
            "create": not options["dry_run"],
        }
        if options["source"] == "mal":
            summary = service.generate_mal_bangumi_candidates(**kwargs)
        elif options["source"] == "vndb":
            summary = service.generate_galgame_candidates(**kwargs)
        else:
            summary = service.generate_anime_candidates(**kwargs)

        if options["evaluate"] and not options["dry_run"]:
            for candidate_id in summary["created_ids"]:
                celery_app.send_task(
                    EVALUATE_TASK,
                    args=[str(candidate_id)],
                    queue="ai",
                )

        mode = "dry-run" if options["dry_run"] else "created"
        self.stdout.write(
            f"[{mode}] {options['source']} "
            f"cursor={summary['cursor_before']}->{summary['cursor_after']} "
            f"of {summary['catalogue_size']} "
            f"window={summary['window']} skipped={summary['skipped_processed']} "
            f"entities={summary['source_entities']} "
            f"candidates_created={summary['candidates_created']} "
            f"blocked={summary['pairs_blocked']} "
            f"below_floor={summary['pairs_below_floor']} "
            f"conflicting={summary['conflicting_pairs']} "
            f"pairs_reported={len(summary['pairs'])}"
        )
        for pair in summary["pairs"][:50]:
            conflict = " !conflict" if pair["hard_conflicts"] else ""
            self.stdout.write(
                f"  {pair['similarity']:.2f} margin={pair['margin']:.2f}{conflict} "
                f"{pair['source_text'][:40]!r} -> {pair['target_text'][:50]!r}"
            )
        if options["evaluate"] and not options["dry_run"]:
            self.stdout.write(
                f"AI evaluation dispatched for {len(summary['created_ids'])} candidates"
            )
