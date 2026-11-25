from __future__ import annotations

import random
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

from agent_harness_lab.core.config import CostConfig, EvalConfig, MockRunnerConfig
from agent_harness_lab.core.results import Outcome, TrialResult
from agent_harness_lab.errors import ConfigError
from agent_harness_lab.evaluation.base import TrialSpec
from agent_harness_lab.harness.base import HarnessAdapter


def price(cost: CostConfig | None, input_tokens: int | None, output_tokens: int | None) -> float | None:
    if cost is None or input_tokens is None or output_tokens is None:
        return None
    return (input_tokens * cost.usd_per_million_input + output_tokens * cost.usd_per_million_output) / 1e6


class MockRunner:
    """Invents results from the seed to exercise the pipeline. No model, harness or verifier runs."""

    simulated = True

    def preflight(
        self, config: EvalConfig, adapters: Mapping[str, HarnessAdapter], plan: Sequence[TrialSpec]
    ) -> dict[str, str]:
        runner = config.runner
        if not isinstance(runner, MockRunnerConfig):
            raise ConfigError("MockRunner needs runner.type 'mock'")
        rates = runner.solve_rate_by_harness
        if unknown := sorted(set(rates) - set(adapters)):
            raise ConfigError(f"solve_rate_by_harness names unknown harnesses: {unknown}")
        if any(not 0 <= rate <= 1 for rate in rates.values()):
            raise ConfigError("solve_rate_by_harness values must be between 0 and 1")
        return {}

    def run(
        self,
        config: EvalConfig,
        plan: Sequence[TrialSpec],
        adapters: Mapping[str, HarnessAdapter],
        run_dir: Path,
    ) -> Iterator[TrialResult]:
        runner = config.runner
        if not isinstance(runner, MockRunnerConfig):
            raise ConfigError("MockRunner needs runner.type 'mock'")
        for spec in plan:
            yield self._trial(config, runner, spec)

    def _trial(self, config: EvalConfig, runner: MockRunnerConfig, spec: TrialSpec) -> TrialResult:
        # Common random numbers across arms: task difficulty is shared, so arms stay paired.
        rng = random.Random(f"{spec.seed}/{spec.harness.name}")  # noqa: S311
        infra, solve, effort = rng.random(), rng.random(), rng.uniform(0.5, 1.5) * runner.effort
        common = {
            "simulated": True,
            "dataset": spec.dataset,
            "task_id": spec.task.task_id,
            "task_hash": spec.task.content_hash,
            "harness": spec.harness.name,
            "harness_version": f"mock-{spec.harness.version}",
            "attempt": spec.attempt,
            "seed": spec.seed,
        }
        if infra < runner.infra_error_rate:
            return TrialResult.model_validate(
                {**common, "outcome": Outcome.INFRA_ERROR, "error": "simulated sandbox failure"}
            )
        solved = solve < runner.solve_rate_by_harness.get(spec.harness.name, runner.solve_rate)
        model_calls = max(1, round(12 * effort))
        input_tokens, output_tokens = model_calls * 2500, model_calls * 150
        return TrialResult.model_validate(
            {
                **common,
                "outcome": Outcome.SOLVED if solved else Outcome.FAILED,
                "rewards": {"reward": float(solved)},
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "tool_calls": model_calls - 1,
                "model_calls": model_calls,
                "latency_s": round(model_calls * 2.5, 3),
                "cost_usd": price(config.cost, input_tokens, output_tokens),
            }
        )
