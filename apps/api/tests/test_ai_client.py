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


@pytest.mark.asyncio
async def test_native_tool_call_keeps_provider_transcript_and_model(monkeypatch, configure):
    monkeypatch.setattr(ai.settings, "ai_model", "fast-model")
    transport = client_factory(
        monkeypatch,
        httpx.Response(
            200,
            json={
                "model": "served-model",
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "function": {
                                        "name": "mal.search_anime",
                                        "arguments": '{"query":"Anime"}',
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            },
        ),
    )
    messages = [{"role": "user", "content": "Find anime"}]
    tools = [{"type": "function", "function": {"name": "mal.search_anime"}}]
    result = await ai.complete_agent(messages=messages, tools=tools, use_case="mal_recall")
    assert result.content == "" and result.model == "served-model"
    assert result.tool_calls == [ai.AgentToolCall("call-1", "mal.search_anime", {"query": "Anime"})]
    sent = transport.post.call_args.kwargs["json"]
    assert sent["messages"] == messages and sent["tools"] == tools and sent["model"] == "fast-model"
    assert "response_format" not in sent
    assert result.usage["input_tokens"] == 12 and result.usage["output_tokens"] == 4


@pytest.mark.asyncio
async def test_interactive_agent_uses_reasoning_model_and_configured_price(monkeypatch, configure):
    monkeypatch.setattr(ai.settings, "ai_reasoning_model", "reasoning-model")
    monkeypatch.setattr(
        ai.settings, "ai_model_prices", {"reasoning-model": {"input": "0.5", "output": "2"}}
    )
    transport = client_factory(
        monkeypatch,
        httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "{}"}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        ),
    )
    result = await ai.complete_agent(
        messages=[{"role": "user", "content": "Question"}], use_case="user_agent_loop"
    )
    assert transport.post.call_args.kwargs["json"]["model"] == "reasoning-model"
    assert result.usage["cost"] == "0.000150"


@pytest.mark.asyncio
async def test_empty_agent_transcript_is_rejected_before_request(monkeypatch, configure):
    transport = client_factory(monkeypatch)
    with pytest.raises(ai.AIError):
        await ai.complete_agent(messages=[])
    transport.post.assert_not_awaited()


def test_malformed_arguments_reach_tool_validation_as_empty_object():
    calls = ai.parse_tool_calls(
        [
            {"id": "1", "function": {"name": "mal.search_anime", "arguments": "broken"}},
            {"id": "2", "function": {"name": "mal.search_anime", "arguments": [1]}},
            {"id": "", "function": {"name": "ignored", "arguments": "{}"}},
            None,
        ]
    )
    assert [call.arguments for call in calls] == [{}, {}]


def test_unknown_model_price_leaves_cost_unset(monkeypatch):
    monkeypatch.setattr(ai.settings, "ai_model_prices", {})
    usage = ai.usage_with_cost("unknown", {"prompt_tokens": 10})
    assert "cost" not in usage
    assert usage["input_tokens"] == 10 and usage["output_tokens"] is None
