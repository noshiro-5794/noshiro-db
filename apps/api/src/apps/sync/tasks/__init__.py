from apps.sync.tasks.airing import run_airing_daily_task
from apps.sync.tasks.anilist import import_anilist_media_task
from apps.sync.tasks.calendar import sync_calendar_task
from apps.sync.tasks.campaign import run_sync_campaign_task
from apps.sync.tasks.frontier import probe_provider_frontiers_task
from apps.sync.tasks.incremental import run_incremental_sync_task
from apps.sync.tasks.linking import link_bangumi_works_task, recall_mal_links_task
from apps.sync.tasks.maintenance import scan_stale_sync_jobs, worker_heartbeat
from apps.sync.tasks.mal import import_mal_media_task, run_mal_season_pipeline_task
from apps.sync.tasks.manual import (
    sync_subject_by_bangumi_id_task,
    sync_subject_by_uuid_task,
)
from apps.sync.tasks.matching import sweep_match_candidates_task
from apps.sync.tasks.refresh import refresh_bangumi_subjects_task
from apps.sync.tasks.season import (
    apply_match_proposals_task,
    check_season_rollover_task,
    reconcile_official_mal_links_task,
    run_season_pipeline_task,
)
from apps.sync.tasks.vndb import import_vndb_work_task, run_vndb_incremental_task

__all__ = (
    "apply_match_proposals_task",
    "check_season_rollover_task",
    "import_anilist_media_task",
    "import_mal_media_task",
    "import_vndb_work_task",
    "link_bangumi_works_task",
    "probe_provider_frontiers_task",
    "recall_mal_links_task",
    "reconcile_official_mal_links_task",
    "refresh_bangumi_subjects_task",
    "run_airing_daily_task",
    "run_incremental_sync_task",
    "run_mal_season_pipeline_task",
    "run_season_pipeline_task",
    "run_sync_campaign_task",
    "run_vndb_incremental_task",
    "scan_stale_sync_jobs",
    "sweep_match_candidates_task",
    "sync_calendar_task",
    "sync_subject_by_bangumi_id_task",
    "sync_subject_by_uuid_task",
    "worker_heartbeat",
)
