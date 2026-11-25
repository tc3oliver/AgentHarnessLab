from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from agent_harness_lab.core.config import EvalConfig, HarnessConfig
from agent_harness_lab.core.results import TrialResult
from agent_harness_lab.dataset.base import TaskRef
from agent_harness_lab.harness.base import HarnessAdapter


@dataclass(frozen=True)
class TrialSpec:
    dataset: str
    task: TaskRef
    harness: HarnessConfig
    attempt: int
    seed: int


class EvaluationRunner(Protocol):
    """Executes a plan. A failed trial is a result; only a broken run raises."""

    simulated: bool

    def preflight(self, config: EvalConfig, adapters: Mapping[str, HarnessAdapter]) -> None:
        """Raise before anything is written if the plan cannot run."""
        ...

    def run(
        self, config: EvalConfig, plan: Sequence[TrialSpec], adapters: Mapping[str, HarnessAdapter]
    ) -> Iterator[TrialResult]:
        """Yield exactly one result per planned trial, in any order."""
        ...
