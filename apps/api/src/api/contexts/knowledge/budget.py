"""Persisted token, cost and execution budgets for native agent loops."""

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class Budget(BaseModel):
    max_input_tokens: int = Field(default=200_000, ge=0)
    max_output_tokens: int = Field(default=200_000, ge=0)
    max_cost_usd: Decimal = Field(default=Decimal("5.00"), ge=0, allow_inf_nan=False)
    max_steps: int = Field(default=100, ge=0)
    input_tokens_used: int = Field(default=0, ge=0)
    output_tokens_used: int = Field(default=0, ge=0)
    cost_used: Decimal = Field(default=Decimal(0), ge=0, allow_inf_nan=False)
    steps_used: int = Field(default=0, ge=0)

    def record_execution(self, usage: dict[str, Any] | None = None) -> None:
        from api.shared.inference import optional_number

        usage = usage or {}
        self.input_tokens_used += int(
            optional_number(usage.get("input_tokens", usage.get("prompt_tokens")), integer=True)
            or 0
        )
        self.output_tokens_used += int(
            optional_number(
                usage.get("output_tokens", usage.get("completion_tokens")), integer=True
            )
            or 0
        )
        self.cost_used += Decimal(optional_number(usage.get("cost")) or 0)
        self.steps_used += 1

    @property
    def exhaustion_reason(self) -> str | None:
        if self.input_tokens_used >= self.max_input_tokens:
            return "input_token_budget_exhausted"
        if self.output_tokens_used >= self.max_output_tokens:
            return "output_token_budget_exhausted"
        if self.cost_used >= self.max_cost_usd:
            return "cost_budget_exhausted"
        if self.steps_used >= self.max_steps:
            return "step_budget_exhausted"
        return None
