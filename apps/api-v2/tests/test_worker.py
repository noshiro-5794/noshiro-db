"""The contract that lets either worker consume either service's tasks."""

from __future__ import annotations

from api.worker.app import app

DJANGO_NAMES = {
    "apps.sync.tasks.maintenance.scan_stale_sync_jobs",
    "apps.sync.tasks.maintenance.worker_heartbeat",
}


def test_tasks_keep_the_django_names() -> None:
    assert set(app.tasks) >= DJANGO_NAMES


def test_sync_tasks_route_to_the_sync_queue() -> None:
    route = app.amqp.router.route({}, "apps.sync.tasks.vndb.import_vndb_work_task")
    assert route["queue"].name == "sync"


def test_ai_tasks_route_to_the_ai_queue() -> None:
    route = app.amqp.router.route({}, "apps.ai.tasks.evaluate_match_candidate_task")
    assert route["queue"].name == "ai"


def test_everything_else_stays_on_realtime() -> None:
    route = app.amqp.router.route({}, "apps.users.tasks.other")
    assert route["queue"].name == "realtime"
