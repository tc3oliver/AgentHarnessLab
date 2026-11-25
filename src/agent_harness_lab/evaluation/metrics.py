from __future__ import annotations

from collections.abc import Sequence
from statistics import fmean, median

from pydantic import BaseModel

from agent_harness_lab.core.results import Outcome, TrialResult


class Summary(BaseModel):
    dataset: str
    harness: str
    n_trials: int
    n_infra_errors: int
    n_graded: int
    n_solved: int
    pass_at_1: float | None
    """First attempts only."""
    mean_input_tokens: float | None
    mean_output_tokens: float | None
    mean_tool_calls: float | None
    median_latency_s: float | None
    cost_per_solved_usd: float | None
    """Cost of all trials, failures and infrastructure errors included, over solved trials."""


def _complete(values: Sequence[float | int | None]) -> list[float] | None:
    """Averages over a partly known column are biased, so an incomplete column is reported as unknown."""
    if not values or any(v is None for v in values):
        return None
    return [float(v) for v in values if v is not None]


def _mean(values: Sequence[float | int | None]) -> float | None:
    known = _complete(values)
    return None if known is None else fmean(known)


def summarize(results: Sequence[TrialResult]) -> list[Summary]:
    cells = sorted({(r.dataset, r.harness) for r in results})
    return [_cell(d, h, [r for r in results if (r.dataset, r.harness) == (d, h)]) for d, h in cells]


def _cell(dataset: str, harness: str, trials: list[TrialResult]) -> Summary:
    graded = [t for t in trials if t.outcome.graded]
    first = [t for t in graded if t.attempt == 1]
    n_solved = sum(t.outcome is Outcome.SOLVED for t in graded)
    latencies = _complete([t.latency_s for t in graded])
    costs = _complete([t.cost_usd for t in trials])
    return Summary(
        dataset=dataset,
        harness=harness,
        n_trials=len(trials),
        n_infra_errors=len(trials) - len(graded),
        n_graded=len(graded),
        n_solved=n_solved,
        pass_at_1=sum(t.outcome is Outcome.SOLVED for t in first) / len(first) if first else None,
        mean_input_tokens=_mean([t.input_tokens for t in graded]),
        mean_output_tokens=_mean([t.output_tokens for t in graded]),
        mean_tool_calls=_mean([t.tool_calls for t in graded]),
        median_latency_s=None if latencies is None else median(latencies),
        cost_per_solved_usd=None if costs is None or not n_solved else sum(costs) / n_solved,
    )
