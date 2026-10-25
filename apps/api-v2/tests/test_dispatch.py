"""Task names and payloads, without a broker."""

import pytest

from api.shared import dispatch


class FakeApp:
    def __init__(self) -> None:
        self.calls = []

    def send_task(self, task, kwargs=None, queue=None):
        self.calls.append((task, kwargs, queue))

        class Result:
            id = "task-1"

        return Result()


@pytest.fixture(autouse=True)
def broker(monkeypatch):
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker/0")


def test_an_import_publishes_to_the_django_task_name() -> None:
    app = FakeApp()
    kwargs = dispatch.import_kwargs(
        provider="vndb", external_id="v123", include_related=True, job_id="job-1"
    )
    assert dispatch.publish(dispatch.task_for_import("vndb"), kwargs, sender=app) == "task-1"
    assert app.calls == [
        (
            "apps.sync.tasks.vndb.import_vndb_work_task",
            {"vndb_id": "v123", "include_related": True, "job_id": "job-1"},
            "sync",
        )
    ]


def test_an_unknown_provider_has_no_task() -> None:
    assert dispatch.task_for_import("nope") is None


def test_without_a_broker_nothing_is_published() -> None:
    import os

    os.environ.pop("CELERY_BROKER_URL", None)
    app = FakeApp()
    assert dispatch.publish(dispatch.SYNC_TASK, {}, sender=app) is None
    assert app.calls == []


def test_a_campaign_publishes_with_its_id() -> None:
    app = FakeApp()
    kwargs = dispatch.sync_kwargs(campaign_id="c-1")
    assert dispatch.publish(dispatch.SYNC_TASK, kwargs, sender=app) == "task-1"
    assert app.calls == [
        (
            "apps.sync.tasks.campaign.run_sync_campaign_task",
            {"campaign_id": "c-1"},
            "sync",
        )
    ]


def test_the_queue_follows_the_old_routing() -> None:
    assert dispatch.queue_for("apps.sync.tasks.vndb.import_vndb_work_task") == "sync"
    assert dispatch.queue_for("apps.ai.tasks.something") == "ai"
    assert dispatch.queue_for("apps.users.tasks.email_tasks.x") == "realtime"


def test_the_message_reaches_a_queue(monkeypatch) -> None:
    """The real Celery app, a memory broker, and the envelope read back."""
    from celery import Celery

    monkeypatch.setenv("CELERY_BROKER_URL", "memory://")
    app = Celery(broker="memory://", backend="cache+memory://")
    app.conf.task_default_queue = "celery"
    app.conf.task_always_eager = False

    dispatch.publish(
        "apps.sync.tasks.campaign.run_sync_campaign_task",
        {"campaign_id": "c-9"},
        sender=app,
    )

    with app.connection_for_read() as connection:
        queue = connection.SimpleQueue("sync")
        message = queue.get(block=True, timeout=5)
        try:
            # Protocol v2: the name rides in the header, the arguments in the body.
            assert message.headers["task"] == "apps.sync.tasks.campaign.run_sync_campaign_task"
            args, kwargs, _ = message.payload
            assert args == []
            assert kwargs == {"campaign_id": "c-9"}
        finally:
            message.ack()
            queue.close()
