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
    AGENT_ERROR = "agent_error"
    """The harness process failed. Graded: it belongs to the system under evaluation."""
    INFRA_ERROR = "infra_error"
    VERIFIER_ERROR = "verifier_error"

    @property
    def graded(self) -> bool:
        """Infrastructure and verifier errors say nothing about the policy, so they are never counted."""
        return self not in {Outcome.INFRA_ERROR, Outcome.VERIFIER_ERROR}


class TrialResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    simulated: bool
    dataset: str
    task_id: str
    task_hash: str
    harness: str
    harness_version: str | None
    """As reported by the runner. For Pi and OpenCode v1 Harbor repeats the pin, which npm installs;
    for OpenCode v2 it checks the installed binary."""
    attempt: int = Field(ge=1)
    seed: int | None
    """Seed that reached the sampler. Null when the harness offers no way to set one."""
    outcome: Outcome
    rewards: dict[str, float] | None = None
    input_tokens: int | None = Field(None, ge=0)
    output_tokens: int | None = Field(None, ge=0)
    tool_calls: int | None = Field(None, ge=0)
    model_calls: int | None = Field(None, ge=0)
    latency_s: float | None = Field(None, ge=0)
    setup_s: float | None = Field(None, ge=0)
    """Starting the sandbox and preparing the harness; not part of latency_s."""
    image: str | None = None
    """Id of the prebuilt image, when one was used."""
    cost_usd: float | None = Field(None, ge=0)
    error: str | None = None

    @model_validator(mode="after")
    def _check(self) -> TrialResult:
        if self.outcome is Outcome.SOLVED and not self.rewards:
            raise ValueError("a solved trial needs verifier rewards")
        if not self.outcome.graded and not self.error:
            raise ValueError("an ungraded trial needs an error message")
        return self

    @property
    def key(self) -> tuple[str, str, str, int]:
        return (self.dataset, self.task_id, self.harness, self.attempt)
