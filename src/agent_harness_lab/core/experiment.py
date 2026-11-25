"""Evaluation lifecycle: load -> plan -> preflight -> run -> report. Nothing is written before preflight."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from agent_harness_lab.core.config import EvalConfig
from agent_harness_lab.core.manifest import MANIFEST_FILE, Manifest, new_manifest
from agent_harness_lab.core.registry import DATASETS, HARNESSES, RUNNERS
from agent_harness_lab.core.results import TrialResult
from agent_harness_lab.dataset.base import DatasetLoader, LoadedDataset
from agent_harness_lab.errors import ConfigError, RunError
from agent_harness_lab.evaluation.base import EvaluationRunner, TrialSpec
from agent_harness_lab.harness.base import HarnessAdapter
from agent_harness_lab.reporting.writers import RESULTS_FILE, ResultWriter, check_formats, write_reports

_OWNED = (MANIFEST_FILE, f"{MANIFEST_FILE}.tmp", RESULTS_FILE, "results.parquet", "report.md")


def trial_seed(seed: int, dataset: str, task_id: str, attempt: int) -> int:
    """Independent of model and harness, so paired arms get the same seed for the same task and attempt."""
    digest = hashlib.sha256(f"{seed}\0{dataset}\0{task_id}\0{attempt}".encode()).digest()
    return int.from_bytes(digest[:4]) & 0x7FFFFFFF


def build_plan(config: EvalConfig, datasets: Sequence[LoadedDataset]) -> list[TrialSpec]:
    return [
        TrialSpec(
            dataset=d.config.name,
            task=task,
            harness=harness,
            attempt=attempt,
            seed=trial_seed(config.seed, d.config.name, task.task_id, attempt),
        )
        for d in datasets
        for task in d.tasks
        for harness in config.harnesses
        for attempt in range(1, config.n_attempts + 1)
    ]


def _prepare_dir(run_dir: Path, overwrite: bool) -> None:
    if run_dir.exists() and any(run_dir.iterdir()):
        if not overwrite:
            raise RunError(f"{run_dir} already exists; use --overwrite or change the experiment name")
        unknown = sorted(p.name for p in run_dir.iterdir() if p.name not in _OWNED)
        if unknown:
            raise RunError(
                f"refusing to overwrite {run_dir}: it contains other files ({', '.join(unknown[:5])})"
            )
        for name in _OWNED:
            (run_dir / name).unlink(missing_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)


def run_evaluation(config: EvalConfig, *, overwrite: bool = False) -> Path:
    # A typo here would turn in-harness gains into transfer gains.
    if unknown := sorted(set(config.trained_on) - set(HARNESSES.names())):
        raise ConfigError(f"trained_on names unknown harnesses: {', '.join(unknown)}")
    loaded: list[LoadedDataset] = []
    for dataset in config.datasets:
        loader: DatasetLoader = DATASETS.get(dataset.source.type)()
        loaded.append(loader.load(dataset))
    adapters: dict[str, HarnessAdapter] = {h.name: HARNESSES.get(h.name)() for h in config.harnesses}
    runner: EvaluationRunner = RUNNERS.get(config.runner.type)()
    plan = build_plan(config, loaded)
    runtime = runner.preflight(config, adapters, plan)
    check_formats(config.report.formats)

    run_dir = Path(config.output_dir) / config.name
    _prepare_dir(run_dir, overwrite)
    manifest = new_manifest(config, loaded, len(plan), runner.simulated, runtime)
    manifest.write(run_dir)

    results: list[TrialResult] = []
    expected = {(s.dataset, s.task.task_id, s.harness.name, s.attempt) for s in plan}
    try:
        with ResultWriter(run_dir / RESULTS_FILE) as writer:
            for result in runner.run(config, plan, adapters, run_dir):
                if result.key not in expected:
                    raise RunError(f"runner returned an unplanned or duplicate trial: {result.key}")
                if result.simulated != runner.simulated:
                    raise RunError("runner returned a result with the wrong 'simulated' flag")
                expected.discard(result.key)
                results.append(result)
                writer.write(result)
        if expected:
            raise RunError(f"runner returned {len(results)} of {len(plan)} planned trials")
        _finish(manifest, results, "completed", None)
        write_reports(run_dir, manifest, results, config.report.formats)
    except BaseException as exc:  # record interrupts too; the exception is always re-raised
        _finish(manifest, results, "failed", f"{type(exc).__name__}: {exc}")
        manifest.write(run_dir)
        raise
    manifest.write(run_dir)
    return run_dir


def _finish(manifest: Manifest, results: list[TrialResult], status: str, error: str | None) -> None:
    manifest.status = "completed" if status == "completed" else "failed"
    manifest.error = error
    manifest.finished_at = datetime.now(UTC)
    manifest.n_recorded = len(results)
    for harness in manifest.harnesses:
        harness.observed_versions = sorted(
            {r.harness_version for r in results if r.harness == harness.name and r.harness_version}
        )
