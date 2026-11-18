from unittest.mock import AsyncMock

from api.worker import vndb_tasks


def test_registered_task_passes_arguments_and_request_identity(monkeypatch):
    importer = AsyncMock(return_value={"entity_id": "fixture"})
    monkeypatch.setattr(vndb_tasks, "import_work", importer)
    execution = vndb_tasks.import_vndb_work_task.apply(
        kwargs={"vndb_id": "v1", "include_related": False, "job_id": "job"}
    )
    assert execution.get() == {"entity_id": "fixture"}
    importer.assert_awaited_once_with(
        "v1", include_related=False, job_id="job", lease_owner=f"celery:{execution.id}"
    )
