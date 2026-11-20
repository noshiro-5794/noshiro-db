from decimal import Decimal

from api.contexts.knowledge.budget import Budget


def test_legacy_budget_load_and_usage_preserve_decimal_cost():
    budget = Budget.model_validate({"max_steps": 3, "cost_used": "0.01"})
    budget.record_execution({"input_tokens": 12, "output_tokens": 8, "cost": "0.00015"})
    budget.record_execution()
    assert budget.steps_used == 2 and budget.cost_used == Decimal("0.01015")
    assert budget.input_tokens_used == 12 and budget.output_tokens_used == 8
    assert budget.exhaustion_reason is None
    budget.record_execution()
    assert budget.exhaustion_reason == "step_budget_exhausted"
    assert Budget.model_validate_json(budget.model_dump_json()) == budget


def test_each_configured_budget_limit_is_enforced():
    for name, reason in [
        ("max_input_tokens", "input_token_budget_exhausted"),
        ("max_output_tokens", "output_token_budget_exhausted"),
        ("max_cost_usd", "cost_budget_exhausted"),
        ("max_steps", "step_budget_exhausted"),
    ]:
        assert Budget.model_validate({name: 0}).exhaustion_reason == reason
