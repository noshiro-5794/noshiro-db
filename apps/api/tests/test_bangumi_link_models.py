from decimal import Decimal

import pytest
from pydantic import ValidationError

from api.contexts.matching.bangumi_models import LinkDecision, search_queries


def test_query_budget_covers_scripts_before_repeated_spellings():
    assert search_queries(["Romanized title", "Other title", "中文名", "かなの題名", "Alias"]) == [
        "かなの題名",
        "Romanized title",
        "中文名",
    ]
    assert search_queries(["First", "First", "Second", "Third", "Fourth"]) == [
        "First",
        "Second",
        "Third",
    ]


@pytest.mark.parametrize("confidence", [-1, 2, "NaN", "Infinity"])
def test_non_finite_or_unbounded_confidence_is_rejected(confidence):
    with pytest.raises(ValidationError):
        LinkDecision.model_validate(
            {"decision": "found", "subject_id": 42, "confidence": confidence}
        )


def test_hallucinated_id_is_an_abstention_even_at_full_confidence():
    result = LinkDecision.model_validate(
        {"decision": "found", "subject_id": "999", "confidence": 1, "reason": "  Claimed match  "}
    ).constrained({42})
    assert result.decision == "not_found" and result.subject_id is None
    assert result.confidence == Decimal(0) and result.reason == "Claimed match"
