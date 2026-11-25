"""Result schema, one record per trial. `None` means unknown and is never replaced by zero."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Outcome(StrEnum):
    SOLVED = "solved"
    FAILED = "failed"
    TIMEOUT = "timeout"
    BUDGET_EXHAUSTED = "budget_exhausted"
    INFRA_ERROR = "infra_error"

    @property
    def graded(self) -> bool:
        """Infrastructure errors say nothing about the policy, so they leave every denominator."""
        return self is not Outcome.INFRA_ERROR


class TrialResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    simulated: bool
    dataset: str
    task_id: str
    task_hash: str
    harness: str
    harness_version: str | None
    """Version observed at run time, not the one requested."""
    attempt: int = Field(ge=1)
    seed: int
    outcome: Outcome
    rewards: dict[str, float] | None = None
    input_tokens: int | None = Field(None, ge=0)
    output_tokens: int | None = Field(None, ge=0)
    tool_calls: int | None = Field(None, ge=0)
    model_calls: int | None = Field(None, ge=0)
    latency_s: float | None = Field(None, ge=0)
    cost_usd: float | None = Field(None, ge=0)
    error: str | None = None

    @model_validator(mode="after")
    def _check(self) -> TrialResult:
        if self.outcome is Outcome.SOLVED and not self.rewards:
            raise ValueError("a solved trial needs verifier rewards")
        if self.outcome is Outcome.INFRA_ERROR and not self.error:
            raise ValueError("an infrastructure error needs an error message")
        return self

    @property
    def key(self) -> tuple[str, str, str, int]:
        return (self.dataset, self.task_id, self.harness, self.attempt)
