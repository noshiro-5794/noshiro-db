from unittest.mock import Mock, patch

from django.test import override_settings

from integrations.ai.gateway import ai_gateway


@override_settings(
    AI_AGENT_API_KEY="test-key",
    AI_AGENT_API_BASE_URL="https://ai.example.test/v1/chat/completions",
    AI_FAST_MODEL="deepseek-ai/DeepSeek-V4-Flash",
    AI_AGENT_TIMEOUT=30,
)
def test_complete_agent_parses_native_tool_calls_and_usage() -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "model": "deepseek-ai/DeepSeek-V4-Flash",
        "usage": {"prompt_tokens": 120, "completion_tokens": 30},
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "type": "function",
                            "function": {
                                "name": "knowledge.search_entities",
                                "arguments": '{"query": "幼女戦記 II", "limit": 10}',
                            },
                        }
                    ],
                }
            }
        ],
    }

    with patch.object(ai_gateway.client, "post", return_value=response) as post:
        completion = ai_gateway.complete_agent(
            messages=[
                {"role": "system", "content": "be precise"},
                {"role": "user", "content": "find it"},
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "knowledge.search_entities",
                        "description": "Search KB.",
                        "parameters": {"type": "object"},
                    },
                }
            ],
        )

    assert len(completion.tool_calls) == 1
    call = completion.tool_calls[0]
    assert call.id == "call_abc"
    assert call.name == "knowledge.search_entities"
    assert call.arguments == {"query": "幼女戦記 II", "limit": 10}
    assert completion.content == ""
    assert completion.usage["input_tokens"] == 120
    body = post.call_args.kwargs["json"]
    assert body["tools"][0]["function"]["name"] == "knowledge.search_entities"
    assert body["messages"][1]["content"] == "find it"


@override_settings(
    AI_AGENT_API_KEY="test-key",
    AI_AGENT_API_BASE_URL="https://ai.example.test/v1/chat/completions",
    AI_FAST_MODEL="deepseek-ai/DeepSeek-V4-Flash",
    AI_AGENT_TIMEOUT=30,
)
def test_complete_agent_returns_final_content_without_tools() -> None:
    response = Mock()
    response.raise_for_status = Mock()
    response.json.return_value = {
        "model": "deepseek-ai/DeepSeek-V4-Flash",
        "usage": {},
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": '{"decision": "no_match"}',
                }
            }
        ],
    }

    with patch.object(ai_gateway.client, "post", return_value=response):
        completion = ai_gateway.complete_agent(
            messages=[{"role": "user", "content": "decide"}]
        )

    assert completion.content == '{"decision": "no_match"}'
    assert completion.tool_calls == []
