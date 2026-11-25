"""Paired comparison of two runs. Every number uses the same trials on both sides."""

from __future__ import annotations

from collections.abc import Sequence
from math import comb

from pydantic import BaseModel

from agent_harness_lab.core.manifest import Manifest
from agent_harness_lab.core.results import Outcome, TrialResult
from agent_harness_lab.errors import ComparisonError


class PairedCell(BaseModel):
    dataset: str
    harness: str
    role: str
    """`in-harness`, `transfer`, or `untrained` when the candidate declares no training harness."""
    n_paired: int
    n_dropped: int
    """First attempts graded on at most one side."""
    base_pass_at_1: float | None
    candidate_pass_at_1: float | None
    gain: float | None
    newly_solved: int
    newly_lost: int
    sign_test_p: float | None
    n_both_solved: int
    tool_call_ratio: float | None
    output_token_ratio: float | None
    latency_ratio: float | None
    """Ratios are candidate / base totals over tasks both solved."""


class Comparison(BaseModel):
    base: str
    candidate: str
    simulated: bool
    mismatches: list[str]
    cells: list[PairedCell]


def sign_test(wins: int, losses: int) -> float:
    """Exact two-sided sign test on discordant pairs (McNemar's exact test)."""
    n = wins + losses
    if n == 0:
        return 1.0
    tail = sum(comb(n, k) for k in range(min(wins, losses) + 1))
    return min(1.0, float(2 * tail / 2**n))


def mismatches(base: Manifest, candidate: Manifest) -> list[str]:
    a, b = base.comparability(), candidate.comparability()
    return [key for key in a if a[key] != b[key]]


def _ratio(pairs: Sequence[tuple[TrialResult, TrialResult]], field: str) -> float | None:
    base = [getattr(b, field) for b, _ in pairs]
    candidate = [getattr(c, field) for _, c in pairs]
    if not pairs or any(v is None for v in (*base, *candidate)) or not sum(base):
        return None
    return float(sum(candidate) / sum(base))


def compare(
    base: Manifest,
    base_results: Sequence[TrialResult],
    candidate: Manifest,
    candidate_results: Sequence[TrialResult],
    *,
    allow_mismatch: bool = False,
) -> Comparison:
    for manifest in (base, candidate):
        if manifest.status != "completed":
            raise ComparisonError(f"run '{manifest.name}' is {manifest.status}, not completed")
    for manifest, results in ((base, base_results), (candidate, candidate_results)):
        if len(results) != manifest.n_recorded:
            raise ComparisonError(
                f"run '{manifest.name}' has {len(results)} results; its manifest says {manifest.n_recorded}"
            )
    differing = mismatches(base, candidate)
    if "simulated" in differing:
        raise ComparisonError("cannot compare a simulated run with a real one")
    if differing and not allow_mismatch:
        raise ComparisonError(
            f"runs differ in {', '.join(differing)}; pass --allow-mismatch to compare anyway"
        )

    a = {r.key: r for r in base_results if r.attempt == 1}
    b = {r.key: r for r in candidate_results if r.attempt == 1}
    cells = []
    for dataset, harness in sorted({(k[0], k[2]) for k in a.keys() | b.keys()}):
        keys = sorted(k for k in a.keys() | b.keys() if (k[0], k[2]) == (dataset, harness))
        pairs = [
            (a[k], b[k])
            for k in keys
            if k in a
            and k in b
            and a[k].outcome.graded
            and b[k].outcome.graded
            # With --allow-mismatch a task may have changed; those are not the same task.
            and a[k].task_hash == b[k].task_hash
        ]
        cells.append(_cell(dataset, harness, candidate, len(keys) - len(pairs), pairs))
    return Comparison(
        base=base.name,
        candidate=candidate.name,
        simulated=base.simulated,
        mismatches=differing,
        cells=cells,
    )


def _cell(
    dataset: str,
    harness: str,
    candidate: Manifest,
    dropped: int,
    pairs: Sequence[tuple[TrialResult, TrialResult]],
) -> PairedCell:
    solved = [(x.outcome is Outcome.SOLVED, y.outcome is Outcome.SOLVED) for x, y in pairs]
    n = len(pairs)
    base_rate = sum(x for x, _ in solved) / n if n else None
    candidate_rate = sum(y for _, y in solved) / n if n else None
    wins = sum(y and not x for x, y in solved)
    losses = sum(x and not y for x, y in solved)
    both = [p for p, (x, y) in zip(pairs, solved, strict=True) if x and y]
    trained = candidate.config.trained_on
    return PairedCell(
        dataset=dataset,
        harness=harness,
        role="untrained" if not trained else "in-harness" if harness in trained else "transfer",
        n_paired=n,
        n_dropped=dropped,
        base_pass_at_1=base_rate,
        candidate_pass_at_1=candidate_rate,
        gain=None if base_rate is None or candidate_rate is None else candidate_rate - base_rate,
        newly_solved=wins,
        newly_lost=losses,
        sign_test_p=sign_test(wins, losses) if n else None,
        n_both_solved=len(both),
        tool_call_ratio=_ratio(both, "tool_calls"),
        output_token_ratio=_ratio(both, "output_tokens"),
        latency_ratio=_ratio(both, "latency_s"),
    )
