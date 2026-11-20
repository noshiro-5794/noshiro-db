import os

from celery import Celery
from celery.beat import Scheduler

from api.config import Settings
from api.shared.dispatch import queue_for
from api.worker.app import app
from api.worker.schedule import periodic_tasks


def test_all_periodic_tasks_are_registered_and_keep_their_queues():
    schedule = periodic_tasks(Settings(_env_file=None))
    assert len(schedule) == 18
    for entry in schedule.values():
        task = entry["task"]
        assert task in app.tasks
        route = app.amqp.router.route({}, task)
        assert route["queue"].name == queue_for(task)
        assert route["queue"].exchange.name == queue_for(task)
    for task in ["worker_heartbeat", "scan_stale_sync_jobs", "scan_stale_sync_states"]:
        assert queue_for("apps.sync.tasks.maintenance." + task) == "realtime"


def test_cron_configuration_preserves_existing_environment_settings(monkeypatch):
    monkeypatch.setenv("SYNC_CALENDAR_CRON_HOUR", "8")
    monkeypatch.setenv("SYNC_CALENDAR_CRON_MINUTE", "12")
    monkeypatch.setenv("SYNC_INCREMENTAL_CRON_HOUR", "9")
    monkeypatch.setenv("SYNC_INCREMENTAL_CRON_MINUTE", "13")
    monkeypatch.setenv("MATCH_CANDIDATE_SWEEP_CRON_HOURS", "6")
    schedule = periodic_tasks(Settings(_env_file=None))
    assert schedule["daily-calendar-sync"]["schedule"].hour == {8}
    assert schedule["daily-calendar-sync"]["schedule"].minute == {12}
    assert schedule["daily-incremental-sync"]["schedule"].hour == {9}
    assert schedule["daily-incremental-sync"]["schedule"].minute == {13}
    assert schedule["sweep-match-candidates"]["schedule"].hour == {0, 6, 12, 18}


def test_beat_loads_all_entries_and_transport_limits_preserve_existing_defaults():
    scheduler = Scheduler(app=app, lazy=True)
    scheduler.setup_schedule()
    assert set(app.conf.beat_schedule) <= set(scheduler.schedule)
    assert app.conf.broker_transport_options["visibility_timeout"] == int(
        os.environ.get("CELERY_VISIBILITY_TIMEOUT", "7200")
    )
    assert app.conf.task_soft_time_limit == 20 and app.conf.task_time_limit == 30
    assert app.conf.accept_content == ["json"]


def test_beat_publishes_scheduled_tasks_to_each_consumed_queue():
    isolated = Celery("schedule-test", broker="memory://", set_as_current=False)
    isolated.conf.update(
        beat_schedule=periodic_tasks(),
        task_routes=app.conf.task_routes,
        task_queues=app.conf.task_queues,
        task_default_queue="realtime",
    )
    try:
        scheduler = Scheduler(app=isolated, lazy=True)
        scheduler.setup_schedule()
        with isolated.connection_for_write() as connection:
            producer = isolated.amqp.Producer(connection)
            for entry_name, queue in [
                ("worker-heartbeat", "realtime"),
                ("daily-calendar-sync", "sync"),
                ("evaluate-pending-matches", "ai"),
            ]:
                entry = scheduler.schedule[entry_name]
                scheduler.apply_async(entry, producer=producer, advance=False)
                with connection.SimpleQueue(queue) as messages:
                    message = messages.get(block=False)
                    assert message.headers["task"] == entry.task
                    message.ack()
    finally:
        isolated.close()
