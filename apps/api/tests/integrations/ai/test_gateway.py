from decimal import Decimal
from unittest.mock import Mock

import pytest
from django.conf import settings
from django.test import override_settings

from integrations.ai import AIProviderError, ai_gateway
from integrations.ai.gateway import (
    USE_CASE_TIERS,
    OpenAICompatibleGateway,
)


class TestResolveModel:
    def test_known_use_case_returns_correct_setting(self) -> None:
        for use_case, tier in USE_CASE_TIERS.items():
            model = ai_gateway.resolve_model(use_case)
            assert model == getattr(settings, tier.value)

    def test_unknown_use_case_falls_back_to_reasoning(self) -> None:
        model = ai_gateway.resolve_model("nonexistent")
        assert model == settings.AI_REASONING_MODEL

    @override_settings(AI_FAST_MODEL="custom-fast")
    def test_matching_use_case_uses_fast_tier(self) -> None:
        assert ai_gateway.resolve_model("entity_matching") == "custom-fast"

    @override_settings(AI_FAST_MODEL="custom-fast")
    def test_completion_use_case_uses_fast_tier(self) -> None:
        assert ai_gateway.resolve_model("info_completion") == "custom-fast"

    @override_settings(AI_REASONING_MODEL="custom-reasoning")
    def test_user_facing_use_case_uses_reasoning_tier(self) -> None:
        assert ai_gateway.resolve_model("user_agent") == "custom-reasoning"
        assert ai_gateway.resolve_model("knowledge_qa") == "custom-reasoning"


class TestConfidence:
    def test_high_confidence(self) -> None:
        c = OpenAICompatibleGateway._confidence({"confidence": "0.99"})
        assert c == Decimal("0.99")

    def test_low_confidence(self) -> None:
        c = OpenAICompatibleGateway._confidence({"confidence": "0.5"})
        assert c == Decimal("0.5")

    def test_missing_confidence_defaults_to_zero(self) -> None:
        c = OpenAICompatibleGateway._confidence({})
        assert c == Decimal("0")

    def test_non_numeric_confidence_defaults_to_zero(self) -> None:
        c = OpenAICompatibleGateway._confidence({"confidence": "high"})
        assert c == Decimal("0")

    def test_boolean_confidence_defaults_to_zero(self) -> None:
        c = OpenAICompatibleGateway._confidence({"confidence": True})
        assert c == Decimal("0")

    def test_none_confidence_defaults_to_zero(self) -> None:
        c = OpenAICompatibleGateway._confidence({"confidence": None})
        assert c == Decimal("0")


class TestCompleteJson:
    def test_raises_without_api_key(self) -> None:
        with (
            override_settings(AI_AGENT_API_KEY=None),
            pytest.raises(AIProviderError, match="not configured"),
        ):
            ai_gateway.complete_json(
                system_prompt="test",
                payload={"key": "value"},
            )

    def test_uses_model_from_use_case(self) -> None:
        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "choices": [{"message": {"content": '{"result": "ok"}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        fake_client = Mock()
        fake_client.post.return_value = fake_response

        gw = OpenAICompatibleGateway(client=fake_client)
        with override_settings(AI_AGENT_API_KEY="sk-test"):
            result, usage = gw.complete_json(
                system_prompt="test",
                payload={"key": "value"},
                use_case="field_normalization",
            )

        assert result == {"result": "ok"}
        assert usage["model"] == settings.AI_FAST_MODEL
        assert usage["input_tokens"] == 10
        assert usage["output_tokens"] == 5

    def test_classification_stays_on_fast_tier_with_low_confidence(self) -> None:
        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "choices": [{"message": {"content": '{"confidence": "0.5"}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        fake_client = Mock()
        fake_client.post.return_value = fake_response

        gw = OpenAICompatibleGateway(client=fake_client)
        with override_settings(AI_AGENT_API_KEY="sk-test"):
            _result, usage = gw.complete_json(
                system_prompt="test",
                payload={"key": "value"},
                use_case="entity_classification",
            )

        assert usage["model"] == settings.AI_FAST_MODEL
        assert fake_client.post.call_count == 1

    def test_http_error_wraps_as_ai_provider_error(self) -> None:
        import httpx

        fake_client = Mock()
        fake_client.post.side_effect = httpx.HTTPError("connection refused")

        gw = OpenAICompatibleGateway(client=fake_client)
        with (
            override_settings(AI_AGENT_API_KEY="sk-test"),
            pytest.raises(AIProviderError, match="connection refused"),
        ):
            gw.complete_json(
                system_prompt="test",
                payload={"key": "value"},
            )

    def test_invalid_json_response_wraps_as_ai_provider_error(self) -> None:
        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "choices": [{"message": {"content": "not json"}}],
        }
        fake_client = Mock()
        fake_client.post.return_value = fake_response

        gw = OpenAICompatibleGateway(client=fake_client)
        with (
            override_settings(AI_AGENT_API_KEY="sk-test"),
            pytest.raises(AIProviderError),
        ):
            gw.complete_json(
                system_prompt="test",
                payload={"key": "value"},
            )

    def test_non_dict_json_output_wraps_as_ai_provider_error(self) -> None:
        fake_response = Mock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "choices": [{"message": {"content": "[1, 2, 3]"}}],
        }
        fake_client = Mock()
        fake_client.post.return_value = fake_response

        gw = OpenAICompatibleGateway(client=fake_client)
        with (
            override_settings(AI_AGENT_API_KEY="sk-test"),
            pytest.raises(AIProviderError, match="JSON output must be an object"),
        ):
            gw.complete_json(
                system_prompt="test",
                payload={"key": "value"},
            )


class TestGatewayProviderName:
    def test_provider_name_is_openai_compatible(self) -> None:
        assert ai_gateway.provider_name == "openai_compatible"


class TestGatewayClientProperty:
    def test_client_property_lazy_init(self) -> None:
        from unittest.mock import patch

        with patch("integrations.ai.gateway.httpx") as mock_httpx:
            mock_client = Mock()
            mock_httpx.Client.return_value = mock_client
            mock_httpx_client_kwargs = Mock(return_value={})

            with patch(
                "integrations.ai.gateway.httpx_client_kwargs",
                mock_httpx_client_kwargs,
            ):
                gw = OpenAICompatibleGateway()
                with override_settings(AI_AGENT_API_KEY="sk-test"):
                    _ = gw.client
                    mock_httpx.Client.assert_called_once()

    def test_client_property_returns_cached(self) -> None:
        fake_client = Mock()
        gw = OpenAICompatibleGateway(client=fake_client)
        assert gw.client is fake_client


class TestGatewayClientWithoutApiKey:
    def test_client_created_without_auth_header(self) -> None:
        from unittest.mock import patch

        with patch("integrations.ai.gateway.httpx") as mock_httpx:
            mock_client = Mock()
            mock_httpx.Client.return_value = mock_client

            with patch(
                "integrations.ai.gateway.httpx_client_kwargs",
                return_value={},
            ):
                gw = OpenAICompatibleGateway()
                with override_settings(AI_AGENT_API_KEY=None):
                    _ = gw.client
                    call_kwargs = mock_httpx.Client.call_args[1]
                    assert "Authorization" not in call_kwargs.get("headers", {})


class TestProviderFailureHandling:
    """A dead account must not be retried forever, and transient errors must be."""

    def test_account_failures_are_terminal(self) -> None:
        from integrations.ai.exceptions import AIProviderError

        assert AIProviderError("nope", status_code=402).retryable is False
        assert AIProviderError("nope", status_code=402).is_account_problem is True
        assert AIProviderError("nope", status_code=401).retryable is False
        assert AIProviderError("nope", status_code=403).is_account_problem is True

    def test_transient_failures_are_retryable(self) -> None:
        from integrations.ai.exceptions import AIProviderError

        assert AIProviderError("nope", status_code=429).retryable is True
        assert AIProviderError("nope", status_code=503).retryable is True
        assert AIProviderError("nope").retryable is True

    def test_a_dead_account_opens_the_breaker_and_is_not_retried(self) -> None:
        from unittest.mock import Mock

        import httpx
        from django.core.cache import cache

        from integrations.ai.gateway import OpenAICompatibleGateway

        cache.delete("noshiro:ai:provider-unavailable")
        response = Mock()
        response.status_code = 402
        response.text = "Payment Required"
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "402", request=Mock(), response=response
        )
        client = Mock()
        client.post.return_value = response

        gateway = OpenAICompatibleGateway(client)
        with pytest.raises(AIProviderError) as excinfo:
            gateway._post(url="https://example.test/v1/chat/completions", payload={})

        assert excinfo.value.status_code == 402

        assert client.post.call_count == 1
        assert OpenAICompatibleGateway.provider_available() is False
        cache.delete("noshiro:ai:provider-unavailable")

    def test_transient_failure_is_retried_then_succeeds(self) -> None:
        from unittest.mock import Mock, patch

        import httpx

        from integrations.ai.gateway import OpenAICompatibleGateway

        failure = Mock()
        failure.status_code = 503
        failure.text = "unavailable"
        failure.raise_for_status.side_effect = httpx.HTTPStatusError(
            "503", request=Mock(), response=failure
        )
        success = Mock()
        success.raise_for_status.return_value = None
        success.json.return_value = {"ok": True}
        client = Mock()
        client.post.side_effect = [failure, success]

        gateway = OpenAICompatibleGateway(client)
        with patch("integrations.ai.gateway.time.sleep"):
            data = gateway._post(url="https://example.test/v1", payload={})

        assert data == {"ok": True}
        assert client.post.call_count == 2

    def test_the_dispatcher_waits_while_the_breaker_is_open(self) -> None:
        from django.core.cache import cache

        from apps.ai.services.matching_batch import ai_matching_batch_service

        cache.set("noshiro:ai:provider-unavailable", "402 Payment Required", timeout=60)
        try:
            result = ai_matching_batch_service.dispatch(limit=100)
        finally:
            cache.delete("noshiro:ai:provider-unavailable")

        assert result == {"dispatched": 0, "reason": "ai_provider_unavailable"}
