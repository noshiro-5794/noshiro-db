"""Periodic task definitions shared by the worker application and beat."""

from typing import Any

from celery.schedules import crontab

from api.config import Settings, settings


def periodic_tasks(config: Settings = settings) -> dict[str, Any]:
    return {
        "daily-calendar-sync": {
            "task": "apps.sync.tasks.calendar.sync_calendar_task",
            "schedule": crontab(
                hour=config.sync_calendar_cron_hour, minute=config.sync_calendar_cron_minute
            ),
        },
        "daily-airing-refresh": {
            "task": "apps.sync.tasks.airing.run_airing_daily_task",
            "schedule": crontab(minute="*/15"),
        },
        "daily-incremental-sync": {
            "task": "apps.sync.tasks.incremental.run_incremental_sync_task",
            "schedule": crontab(
                hour=config.sync_incremental_cron_hour, minute=config.sync_incremental_cron_minute
            ),
        },
        "season-source-refresh": {
            "task": "apps.sync.tasks.season.run_season_pipeline_task",
            "schedule": crontab(hour=2, minute=30),
        },
        "season-rollover-check": {
            "task": "apps.sync.tasks.season.check_season_rollover_task",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "evaluate-pending-matches": {
            "task": "apps.ai.tasks.evaluate_pending_candidates_task",
            "schedule": crontab(minute="*/30"),
        },
        "refresh-popularity": {
            "task": "apps.index.tasks.popularity.refresh_popularity_task",
            "schedule": crontab(hour=5, minute=15),
        },
        "reconcile-official-mal-links": {
            "task": "apps.sync.tasks.season.reconcile_official_mal_links_task",
            "schedule": crontab(hour=4, minute=45),
        },
        "probe-provider-frontiers": {
            "task": "apps.sync.tasks.frontier.probe_provider_frontiers_task",
            "schedule": crontab(hour=4, minute=30),
        },
        "refresh-bangumi-subjects": {
            "task": "apps.sync.tasks.refresh.refresh_bangumi_subjects_task",
            "schedule": crontab(hour=5, minute=0),
        },
        "vndb-incremental": {
            "task": "apps.sync.tasks.vndb.run_vndb_incremental_task",
            "schedule": crontab(hour=5, minute=30),
        },
        "apply-match-proposals": {
            "task": "apps.sync.tasks.season.apply_match_proposals_task",
            "schedule": crontab(minute="*/30"),
        },
        "sweep-match-candidates": {
            "task": "apps.sync.tasks.matching.sweep_match_candidates_task",
            "schedule": crontab(minute=0, hour=f"*/{config.match_candidate_sweep_cron_hours}"),
        },
        "bangumi-link-sweep": {
            "task": "apps.sync.tasks.linking.link_bangumi_works_task",
            "schedule": crontab(hour=6, minute=0),
        },
        "mal-link-recall": {
            "task": "apps.sync.tasks.linking.recall_mal_links_task",
            "schedule": crontab(minute=45, hour="*/6"),
        },
        "worker-heartbeat": {
            "task": "apps.sync.tasks.maintenance.worker_heartbeat",
            "schedule": 60.0,
        },
        "stale-sync-job-scan": {
            "task": "apps.sync.tasks.maintenance.scan_stale_sync_jobs",
            "schedule": 300.0,
        },
        "stale-sync-state-scan": {
            "task": "apps.sync.tasks.maintenance.scan_stale_sync_states",
            "schedule": 300.0,
        },
    }
