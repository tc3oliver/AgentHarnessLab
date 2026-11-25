import pytest
from conftest import trial
from pydantic import ValidationError

from agent_harness_lab.core.config import EvalConfig
from agent_harness_lab.core.manifest import Manifest, new_manifest
from agent_harness_lab.core.results import TrialResult
from agent_harness_lab.errors import ComparisonError
from agent_harness_lab.evaluation.compare import compare, sign_test
from agent_harness_lab.evaluation.metrics import summarize
from agent_harness_lab.rollout.schema import Trajectory, Turn


def test_summary_rules() -> None:
    [s] = summarize(
        [
            trial("a", "solved", tool_calls=2, cost_usd=1.0, latency_s=1),
            trial("b", "timeout", tool_calls=4, cost_usd=2.0, latency_s=3),
            trial("c", "budget_exhausted", tool_calls=6, cost_usd=3.0, latency_s=5),
            trial("d", "infra_error", cost_usd=4.0),
        ]
    )
    assert (s.n_trials, s.n_graded, s.n_infra_errors, s.n_solved) == (4, 3, 1, 1)
    assert s.pass_at_1 == pytest.approx(1 / 3)
    assert s.mean_tool_calls == 4 and s.median_latency_s == 3
    assert s.cost_per_solved_usd == 10.0
    assert s.mean_output_tokens is None


def test_pass_at_1_uses_first_attempts_only() -> None:
    [s] = summarize([trial("a", "failed"), trial("a", "solved", attempt=2)])
    assert s.pass_at_1 == 0.0 and s.n_solved == 1


def test_unknown_is_not_zero() -> None:
    [s] = summarize([trial("a", tool_calls=2, cost_usd=1.0), trial("b", cost_usd=None)])
    assert s.mean_tool_calls is None and s.cost_per_solved_usd is None
    [s] = summarize([trial("a", "infra_error")])
    assert s.pass_at_1 is None
    [s] = summarize([trial("a", "failed", cost_usd=1.0)])
    assert s.cost_per_solved_usd is None


def test_result_invariants() -> None:
    with pytest.raises(ValidationError):
        trial(rewards=None)
    with pytest.raises(ValidationError):
        trial(outcome="infra_error", error=None)
    with pytest.raises(ValidationError):
        trial(attempt=0)


@pytest.mark.parametrize(
    ("wins", "losses", "p"),
    [(0, 0, 1.0), (1, 1, 1.0), (15, 2, 0.00235), (16, 2, 0.00131), (2, 15, 0.00235)],
)
def test_sign_test(wins: int, losses: int, p: float) -> None:
    """15/2 and 16/2 are the Pi adapter card's pairs (p = 0.0023 and 0.0013)."""
    assert sign_test(wins, losses) == pytest.approx(p, abs=1e-5)


def manifest(config: EvalConfig, **over: object) -> Manifest:
    m = new_manifest(config, [], 0, simulated=True, runtime={})
    return m.model_copy(update={"status": "completed", **over})


def test_compare(config: EvalConfig) -> None:
    base = [
        trial("a", "failed"),
        trial("b", "solved", tool_calls=10),
        trial("c", "solved"),
        trial("d", "infra_error"),
        trial("e", "solved"),
    ]
    cand = [
        trial("a", "solved"),
        trial("b", "solved", tool_calls=5),
        trial("c", "failed"),
        trial("d", "solved"),
    ]
    trained = config.model_copy(update={"trained_on": ["opencode"]})
    result = compare(manifest(config, n_recorded=5), base, manifest(trained, n_recorded=4), cand)
    [cell] = result.cells
    assert cell.role == "transfer"
    assert (cell.n_paired, cell.n_dropped) == (3, 2)
    assert (cell.newly_solved, cell.newly_lost, cell.gain) == (1, 1, 0.0)
    assert cell.n_both_solved == 1 and cell.tool_call_ratio == 0.5
    assert cell.output_token_ratio is None


def test_compare_refusals(config: EvalConfig) -> None:
    ok = manifest(config)
    with pytest.raises(ComparisonError, match="not completed"):
        compare(ok, [], manifest(config, status="failed"), [])
    with pytest.raises(ComparisonError, match="simulated"):
        compare(ok, [], manifest(config, simulated=False), [], allow_mismatch=True)
    with pytest.raises(ComparisonError, match="manifest says 3"):
        compare(ok, [], manifest(config, n_recorded=3), [])
    other = manifest(config.model_copy(update={"n_attempts": 2}))
    with pytest.raises(ComparisonError, match="n_attempts"):
        compare(ok, [], other, [])
    assert compare(ok, [], other, [], allow_mismatch=True).mismatches == ["n_attempts"]


def test_changed_tasks_are_never_paired(config: EvalConfig) -> None:
    def one(h: str) -> list[TrialResult]:
        return [trial("a", task_hash=h)]

    m = manifest(config, n_recorded=1)
    [cell] = compare(m, one("x"), m, one("y")).cells
    assert cell.sign_test_p is None
    assert cell.n_paired == 0 and cell.gain is None and cell.n_dropped == 1


def test_trajectory_contract() -> None:
    turn = Turn(
        prompt_token_ids=[10, 11],
        completion_token_ids=[12, 13],
        logprobs=[-0.1, -0.2],
        loss_mask=[0, 0, 1, 0],
    )
    t = Trajectory(task_id="t", harness="pi", policy_version=0, turns=[turn], reward=None)
    assert t.group == ("t", "pi")
    for bad in ({"logprobs": [0.0]}, {"loss_mask": [1, 0, 1, 0]}, {"loss_mask": [1, 1]}):
        with pytest.raises(ValidationError):
            Turn.model_validate({**turn.model_dump(), **bad})
