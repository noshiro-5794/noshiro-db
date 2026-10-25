"""Task names and payloads, without a broker."""

import pytest

from api.shared import dispatch


class FakeApp:
    def __init__(self) -> None:
        self.calls = []

    def send_task(self, task, kwargs=None):
        self.calls.append((task, kwargs))

        class Result:
            id = "task-1"

        return Result()


@pytest.fixture(autouse=True)
def broker(monkeypatch):
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://broker/0")


def test_an_import_publishes_to_the_django_task_name() -> None:
    app = FakeApp()
    kwargs = dispatch.import_kwargs(external_id="v123", include_related=True, job_id="job-1")
    assert dispatch.publish(dispatch.task_for_import("vndb"), kwargs, sender=app) == "task-1"
    assert app.calls == [
        (
            "apps.sync.tasks.vndb.import_vndb_work_task",
            {"external_id": "v123", "include_related": True, "job_id": "job-1"},
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
