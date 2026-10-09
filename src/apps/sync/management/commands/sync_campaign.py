import time

from django.core.management.base import BaseCommand, CommandError

from apps.sync.models import SyncCampaign
from apps.sync.services.campaign import (
    PROVIDERS,
    campaign_idempotency_key,
    sync_campaign_service,
)


class Command(BaseCommand):
    help = "Run a durable provider-wide sync campaign."

    def add_arguments(self, parser):
        # Taken from the registry so a new provider cannot be missing here.
        parser.add_argument("provider", choices=tuple(sorted(PROVIDERS)))
        parser.add_argument(
            "--campaign-type",
            choices=("full", "incremental"),
            default="full",
        )
        parser.add_argument(
            "--ai-mode",
            choices=[value for value, _ in SyncCampaign.AIMode.choices],
            default=SyncCampaign.AIMode.SHADOW,
        )
        parser.add_argument("--idempotency-key", default="")
        parser.add_argument("--page-size", type=int, default=100)
        parser.add_argument(
            "--ai-sample-size",
            type=int,
            default=0,
            help="Optional cap for AI processing; zero processes every successful item.",
        )
        parser.add_argument("--max-items", type=int)
        parser.add_argument(
            "--max-pages",
            type=int,
            help=(
                "Cap discovery at this many pages per campaign step for bounded, "
                "resumable batch runs (truncates discovery and proceeds to fetch)."
            ),
        )
        parser.add_argument(
            "--discovery-pages-per-step",
            type=int,
            help="Pages of discovery consumed per invocation (default 1).",
        )
        parser.add_argument(
            "--watch",
            action="store_true",
            help=(
                "Keep stepping the campaign until it reaches a terminal state, "
                "printing one progress line per step. A long full sync runs for "
                "hours, so this is the mode to run under tmux."
            ),
        )
        parser.add_argument(
            "--watch-delay",
            type=float,
            default=15.0,
            help="Seconds to wait between watch steps (default 15).",
        )
        parser.add_argument(
            "--watch-timeout",
            type=float,
            default=0.0,
            help="Stop watching after this many seconds (zero runs until terminal).",
        )

    def handle(self, *args, **options):
        provider = options["provider"]
        campaign_type = options["campaign_type"]
        parameters = {
            "page_size": options["page_size"],
            "ai_sample_size": options["ai_sample_size"],
        }
        if options["max_pages"] is not None:
            parameters["max_pages"] = options["max_pages"]
        if options["discovery_pages_per_step"] is not None:
            parameters["discovery_pages_per_step"] = options["discovery_pages_per_step"]
        key = options["idempotency_key"] or campaign_idempotency_key(
            provider_slug=provider,
            campaign_type=campaign_type,
            parameters=parameters,
        )
        try:
            campaign = sync_campaign_service.create_campaign(
                provider_slug=provider,
                campaign_type=campaign_type,
                ai_mode=options["ai_mode"],
                parameters=parameters,
                idempotency_key=key,
            )
            if options["watch"]:
                sample: dict = {}
                campaign = sync_campaign_service.watch(
                    campaign,
                    delay=options["watch_delay"],
                    max_items=options.get("max_items"),
                    timeout=options["watch_timeout"],
                    on_step=lambda stepped: self.stdout.write(
                        progress_line(stepped, sample)
                    ),
                )
            else:
                campaign = sync_campaign_service.run(
                    campaign, max_items=options.get("max_items")
                )
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Campaign {campaign.pk} {campaign.provider_slug}: {campaign.status}"
            )
        )


def progress_line(campaign: SyncCampaign, sample: dict) -> str:
    """One progress line with a rate measured between steps, not since boot.

    A campaign keeps its counters across restarts, so a cumulative average would
    divide work already done by this run's uptime and report an ETA that is
    orders of magnitude too short.
    """
    now = time.monotonic()
    done = campaign.processed_items
    previous_at, previous_done = sample.get("at"), sample.get("done")
    if previous_at is not None and now > previous_at:
        instant = max(0.0, (done - previous_done) / (now - previous_at))
        previous_rate = sample.get("rate")
        sample["rate"] = (
            instant if previous_rate is None else previous_rate * 0.6 + instant * 0.4
        )
    sample["at"], sample["done"] = now, done
    rate = sample.get("rate") or 0.0
    remaining = max(0, campaign.total_items - done)
    eta = f"{remaining / rate / 3600:.1f}h" if rate > 0.01 else "?"
    return (
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} {campaign.status} "
        f"proc {done}/{campaign.total_items} "
        f"synced {campaign.synced_items} skipped {campaign.skipped_items} "
        f"failed {campaign.failed_items} {rate:.2f}/s eta {eta}"
    )
