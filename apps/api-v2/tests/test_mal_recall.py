import pytest
from pydantic import ValidationError

from api.contexts.matching.mal_models import RecallDecision, observed_mal_ids
from api.worker import linking_tasks
from api.worker.app import app


def test_legacy_matched_decision_normalizes_to_found():
    decision = RecallDecision.model_validate({"decision": "matched", "mal_id": 42})
    assert decision.decision == "found" and decision.mal_id == 42


@pytest.mark.parametrize("value", [True, 0, -1, 1.5])
def test_mal_identifiers_require_positive_integers(value):
    with pytest.raises(ValidationError):
        RecallDecision.model_validate({"decision": "found", "mal_id": value})


def test_observed_ids_follow_mal_tool_fields_and_ignore_unrelated_ids():
    assert observed_mal_ids("mal.search_anime", {"results": [{"id": 42}, {"id": True}]}) == {42}
    assert observed_mal_ids("knowledge.search_entities", {"results": [{"id": 42}]}) == set()
    assert observed_mal_ids(
        "knowledge.get_entity",
        {
            "entity": {
                "id": 42,
                "sources": [
                    {"provider": "mal", "namespace": "anime", "external_id": "123"},
                    {"provider": "bangumi", "namespace": "subject", "external_id": "456"},
                ],
            }
        },
    ) == {123}


def test_recall_task_retains_queue_limits_and_clamps_batch(monkeypatch):
    task = app.tasks["apps.sync.tasks.linking.recall_mal_links_task"]
    assert task.queue == "sync" and task.soft_time_limit == 3600 and task.time_limit == 3900
    called = {}

    async def recall(**kwargs):
        called.update(kwargs)
        return {"processed": 0}

    monkeypatch.setattr(linking_tasks.mal_recall, "run_missing", recall)
    monkeypatch.setenv("MAL_LINK_RECALL_BATCH_SIZE", "3")
    assert task.run() == {"processed": 0}
    assert called == {"limit": 3, "evaluate": True, "force": False}
    task.run(limit=0, force=True)
    assert called == {"limit": 1, "evaluate": True, "force": True}
