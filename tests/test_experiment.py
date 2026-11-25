import json
from collections.abc import Iterator
from pathlib import Path

import pytest

from agent_harness_lab.core import experiment
from agent_harness_lab.core.config import EvalConfig
from agent_harness_lab.core.experiment import run_evaluation, trial_seed
from agent_harness_lab.core.manifest import Manifest
from agent_harness_lab.core.results import Outcome, TrialResult
from agent_harness_lab.errors import ConfigError, RunError
from agent_harness_lab.evaluation.runners import MockRunner
from agent_harness_lab.reporting.writers import read_results


def test_run_is_deterministic_and_complete(config: EvalConfig) -> None:
    run_dir = run_evaluation(config)
    first = (run_dir / "results.jsonl").read_text()
    manifest = Manifest.read(run_dir)
    assert manifest.status == "completed" and manifest.simulated
    assert manifest.n_planned == manifest.n_recorded == 12
    assert manifest.datasets[0].revision.startswith("sha256:")
    assert manifest.harnesses[0].observed_versions == ["mock-1.0"]
    assert len(manifest.config_hash) == 64
    assert "SIMULATED" in (run_dir / "report.md").read_text()
    run_evaluation(config, overwrite=True)
    assert (run_dir / "results.jsonl").read_text() == first


def test_seed_changes_results(config: EvalConfig) -> None:
    run_dir = run_evaluation(config)
    first = read_results(run_dir)
    run_evaluation(config.model_copy(update={"seed": 8}), overwrite=True)
    assert read_results(run_dir) != first


def test_trial_seed_is_stable() -> None:
    assert trial_seed(0, "d", "t", 1) == trial_seed(0, "d", "t", 1)
    assert len({trial_seed(0, "d", "t", a) for a in range(50)}) == 50


def test_existing_runs_are_protected(config: EvalConfig) -> None:
    run_dir = run_evaluation(config)
    with pytest.raises(RunError, match="already exists"):
        run_evaluation(config)
    (run_dir / "notes.txt").write_text("mine")
    with pytest.raises(RunError, match="refusing"):
        run_evaluation(config, overwrite=True)
    assert (run_dir / "notes.txt").read_text() == "mine"
    assert (run_dir / "manifest.json").exists()


def test_failure_keeps_finished_trials(config: EvalConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    real = MockRunner.run

    def broken(self: MockRunner, *args: object) -> Iterator[TrialResult]:
        it = real(self, *args)  # type: ignore[arg-type]
        yield next(it)
        raise OSError("disk gone")

    monkeypatch.setattr(MockRunner, "run", broken)
    with pytest.raises(OSError, match="disk gone"):
        run_evaluation(config)
    run_dir = Path(config.output_dir) / config.name
    manifest = Manifest.read(run_dir)
    assert manifest.status == "failed" and "disk gone" in (manifest.error or "")
    assert manifest.n_recorded == len(read_results(run_dir)) == 1


@pytest.mark.parametrize("fault", ["missing", "duplicate", "unsimulated"])
def test_misbehaving_runners_are_caught(
    config: EvalConfig, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    real = MockRunner.run

    def bad(self: MockRunner, *args: object) -> Iterator[TrialResult]:
        results = list(real(self, *args))  # type: ignore[arg-type]
        if fault == "missing":
            return iter(results[:-1])
        if fault == "duplicate":
            return iter([*results, results[0]])
        return iter([results[0].model_copy(update={"simulated": False})])

    monkeypatch.setattr(MockRunner, "run", bad)
    with pytest.raises(RunError):
        run_evaluation(config)


def test_nothing_is_written_when_preflight_fails(config: EvalConfig) -> None:
    bad = config.model_copy(
        update={"runner": config.runner.model_copy(update={"solve_rate_by_harness": {"typo": 0.5}})}
    )
    with pytest.raises(ConfigError, match="typo"):
        run_evaluation(bad)
    assert not Path(config.output_dir).exists()


def test_unknown_harness_lists_choices(config: EvalConfig) -> None:
    bad = config.model_copy(update={"harnesses": [config.harnesses[0].model_copy(update={"name": "nope"})]})
    with pytest.raises(ConfigError, match="available: opencode, pi"):
        run_evaluation(bad)


def test_infra_errors_and_parquet(config: EvalConfig) -> None:
    import pyarrow.parquet as pq

    data = config.model_dump()
    data["runner"]["infra_error_rate"] = 0.5
    data["report"]["formats"] = ["parquet", "markdown"]
    run_dir = run_evaluation(EvalConfig.model_validate(data))
    results = read_results(run_dir)
    assert {r.outcome for r in results} >= {Outcome.INFRA_ERROR}
    rows = pq.read_table(run_dir / "results.parquet").to_pylist()
    assert len(rows) == len(results)
    for row, result in zip(rows, results, strict=True):
        rewards = None if row["rewards"] is None else dict(row["rewards"])
        assert rewards == result.rewards and row["input_tokens"] == result.input_tokens


def test_corrupt_results(config: EvalConfig) -> None:
    run_dir = run_evaluation(config)
    path = run_dir / "results.jsonl"
    path.write_text(path.read_text() + path.read_text().splitlines()[0] + "\n")
    with pytest.raises(RunError, match="duplicate"):
        read_results(run_dir)
    path.write_text("{}\n")
    with pytest.raises(RunError, match="invalid record"):
        read_results(run_dir)
    (run_dir / "manifest.json").write_text(json.dumps({"x": 1}))
    with pytest.raises(RunError, match="invalid manifest"):
        Manifest.read(run_dir)


def test_parquet_dependency_is_checked_first(config: EvalConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    def missing(formats: object) -> None:
        raise ConfigError("parquet")

    monkeypatch.setattr(experiment, "check_formats", missing)
    with pytest.raises(ConfigError):
        run_evaluation(config)
    assert not Path(config.output_dir).exists()


def test_trained_on_typo(config: EvalConfig) -> None:
    with pytest.raises(ConfigError, match="Pi"):
        run_evaluation(config.model_copy(update={"trained_on": ["Pi"]}))


def test_stale_temporary_manifest_does_not_block_overwrite(config: EvalConfig) -> None:
    run_dir = run_evaluation(config)
    (run_dir / "manifest.json.tmp").write_text("{")
    run_evaluation(config, overwrite=True)
    assert not (run_dir / "manifest.json.tmp").exists()
