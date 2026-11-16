from unittest.mock import AsyncMock

import httpx
import pytest

from api.shared import ai


@pytest.fixture
def configure(monkeypatch):
    monkeypatch.setattr(ai.settings, "ai_base_url", "https://provider.test/chat/completions")
    monkeypatch.setattr(ai.settings, "ai_api_key", "test-key")
    monkeypatch.setattr(ai, "provider_available", AsyncMock(return_value=True))
    cooldown = AsyncMock()
    monkeypatch.setattr(ai, "mark_unavailable", cooldown)
    return cooldown


def client_factory(monkeypatch, response=None, error=None):
    transport = AsyncMock()
    if error:
        transport.post.side_effect = error
    else:
        transport.post.return_value = response

    class Context:
        async def __aenter__(self):
            return transport

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(ai.httpx, "AsyncClient", lambda **kwargs: Context())
    return transport


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,retryable", [(401, False), (402, False), (403, False), (429, True), (503, True)]
)
async def test_provider_errors_have_bounded_retry_classification(
    monkeypatch, configure, status, retryable
):
    client_factory(monkeypatch, httpx.Response(status))
    with pytest.raises(ai.AIError) as raised:
        await ai.complete_json(system="system", payload={})
    assert raised.value.retryable == retryable
    assert raised.value.status_code == status
    if status in {401, 402, 403}:
        configure.assert_awaited_once_with(status)
    else:
        configure.assert_not_awaited()


@pytest.mark.asyncio
async def test_cooldown_prevents_another_provider_request(monkeypatch, configure):
    monkeypatch.setattr(ai, "provider_available", AsyncMock(return_value=False))
    client = client_factory(monkeypatch)
    with pytest.raises(ai.AIError):
        await ai.complete_json(system="system", payload={})
    client.post.assert_not_awaited()


@pytest.mark.asyncio
async def test_timeout_is_retryable(monkeypatch, configure):
    client_factory(monkeypatch, error=httpx.ReadTimeout("timeout"))
    with pytest.raises(ai.AIError) as raised:
        await ai.complete_json(system="system", payload={})
    assert raised.value.retryable


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body", [{"choices": []}, {"choices": [{"message": {"content": "[]"}}]}, [1]]
)
async def test_invalid_json_output_is_terminal(monkeypatch, configure, body):
    client_factory(monkeypatch, httpx.Response(200, json=body))
    with pytest.raises(ai.AIError) as raised:
        await ai.complete_json(system="system", payload={})
    assert not raised.value.retryable


def test_ai_tasks_register_queue_and_retry_limits():
    from api.worker.app import app

    task = app.tasks["apps.ai.tasks.evaluate_match_candidate_task"]
    assert task.queue == "ai"
    assert task.max_retries == 3
    assert "apps.ai.tasks.evaluate_pending_candidates_task" in app.tasks
