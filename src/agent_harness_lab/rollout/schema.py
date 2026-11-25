"""Trajectory records for training. Token fields come from the engine; they are never re-tokenised locally.

The producer (OpenEnv capture, planned for v0.2) is not implemented. The shape mirrors a turn of OpenEnv's
`TrainingTrace`: the loss mask covers prompt and completion, and prompt positions are zero.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    failed: bool | None = None


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    prompt_token_ids: list[int]
    completion_token_ids: list[int]
    logprobs: list[float]
    loss_mask: list[Literal[0, 1]]
    tool_calls: list[ToolCall] = []

    @model_validator(mode="after")
    def _lengths(self) -> Turn:
        if len(self.logprobs) != len(self.completion_token_ids):
            raise ValueError("one logprob is required per completion token")
        if len(self.loss_mask) != len(self.prompt_token_ids) + len(self.completion_token_ids):
            raise ValueError("loss_mask must cover prompt and completion")
        if any(self.loss_mask[: len(self.prompt_token_ids)]):
            raise ValueError("prompt tokens must not be trained on")
        return self


class Trajectory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    harness: str
    policy_version: int
    turns: list[Turn]
    reward: float | None
    """None means the rollout could not be scored. It must not be trained on as zero."""

    @property
    def group(self) -> tuple[str, str]:
        """The advantage group: rewards are only compared within one task and one harness."""
        return (self.task_id, self.harness)
