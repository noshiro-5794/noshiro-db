from unittest.mock import patch

import pytest
from celery.exceptions import Retry

from apps.ai.tasks import (
    classify_entity_task,
    complete_missing_schedule_slots_task,
    evaluate_match_candidate_task,
    extract_observation_evidence_task,
)
from integrations.ai import AIProviderError


@pytest.mark.django_db(transaction=True)
class TestEvaluateMatchCandidateTask:
    def test_returns_proposal_id(self) -> None:
        with patch("apps.ai.tasks.ai_matching_service.evaluate") as mock_evaluate:
            mock_evaluate.return_value.id = "proposal-uuid"
            result = evaluate_match_candidate_task("candidate-uuid")
            assert result == "proposal-uuid"
            mock_evaluate.assert_called_once_with(candidate_id="candidate-uuid")


@pytest.mark.django_db(transaction=True)
class TestClassifyEntityTask:
    def test_returns_proposal_id(self) -> None:
        with patch(
            "apps.ai.tasks.ai_knowledge_proposal_service.classify_entity"
        ) as mock_classify:
            mock_classify.return_value.id = "proposal-uuid"
            result = classify_entity_task("entity-uuid")
            assert result == "proposal-uuid"
            mock_classify.assert_called_once_with(entity_id="entity-uuid")


@pytest.mark.django_db(transaction=True)
class TestExtractObservationEvidenceTask:
    def test_returns_proposal_id(self) -> None:
        with patch(
            "apps.ai.tasks.ai_knowledge_proposal_service.extract_evidence"
        ) as mock_extract:
            mock_extract.return_value.id = "proposal-uuid"
            result = extract_observation_evidence_task("obs-uuid", "entity-uuid")
            assert result == "proposal-uuid"
            mock_extract.assert_called_once_with(
                observation_id="obs-uuid", entity_id="entity-uuid"
            )


@pytest.mark.django_db(transaction=True)
class TestProviderErrorRetries:
    def test_terminal_error_is_not_retried(self) -> None:
        error = AIProviderError("Insufficient Balance", status_code=402)
        with patch("apps.ai.tasks.ai_matching_service.evaluate", side_effect=error):
            result = evaluate_match_candidate_task.apply(args=["candidate-uuid"])
        assert result.state == "IGNORED"

    def test_transient_error_is_retried(self) -> None:
        error = AIProviderError("connection reset")
        with (
            patch("apps.ai.tasks.ai_matching_service.evaluate", side_effect=error),
            pytest.raises(Retry),
        ):
            evaluate_match_candidate_task.apply(args=["candidate-uuid"])


@pytest.mark.django_db(transaction=True)
class TestTerminalErrorsAcrossTasks:
    """A 402 means the account cannot call the provider; no task retries it."""

    error = AIProviderError("Insufficient Balance", status_code=402)

    def test_classify_is_not_retried(self) -> None:
        with patch(
            "apps.ai.tasks.ai_knowledge_proposal_service.classify_entity",
            side_effect=self.error,
        ):
            result = classify_entity_task.apply(args=["entity-uuid"])
        assert result.state == "IGNORED"

    def test_extract_is_not_retried(self) -> None:
        with patch(
            "apps.ai.tasks.ai_knowledge_proposal_service.extract_evidence",
            side_effect=self.error,
        ):
            result = extract_observation_evidence_task.apply(
                args=["observation-uuid", "entity-uuid"]
            )
        assert result.state == "IGNORED"

    def test_schedule_completion_is_not_retried(self) -> None:
        with patch(
            "apps.ai.tasks.schedule_completion_service.run", side_effect=self.error
        ):
            result = complete_missing_schedule_slots_task.apply(
                kwargs={"limit": 10, "apply": False}
            )
        assert result.state == "IGNORED"
