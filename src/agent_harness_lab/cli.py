from __future__ import annotations

import signal
import sys
from pathlib import Path
from typing import Annotated

import typer

from agent_harness_lab import __version__
from agent_harness_lab.core.config import EvalConfig, TrainConfig, load_dataset_config, load_experiment
from agent_harness_lab.core.experiment import run_evaluation
from agent_harness_lab.core.manifest import Manifest
from agent_harness_lab.core.registry import DATASETS, TRAINERS
from agent_harness_lab.dataset.audit import audit as run_audit
from agent_harness_lab.dataset.base import LoadedDataset
from agent_harness_lab.errors import AgentLabError, ConfigError, LeakageError
from agent_harness_lab.evaluation.compare import compare as compare_runs
from agent_harness_lab.reporting.writers import read_results, render_comparison, render_run

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
    help="Reproducible cross-harness agent evaluation. Training is not implemented yet.",
)
ConfigOption = Annotated[Path, typer.Option("--config", "-c", help="Experiment YAML file.")]


def _version(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit


@app.callback()
def _root(
    version: Annotated[bool, typer.Option("--version", callback=_version, is_eager=True)] = False,
) -> None: ...


@app.command("eval")
def eval_(
    config: ConfigOption,
    overwrite: Annotated[bool, typer.Option(help="Replace an earlier run of the same name.")] = False,
) -> None:
    """Run an evaluation with the mock or the Harbor runner."""
    experiment = load_experiment(config)
    if not isinstance(experiment, EvalConfig):
        raise ConfigError(f"{config} is a training config; use 'agentlab train'")
    run_dir = run_evaluation(experiment, overwrite=overwrite)
    typer.echo(render_run(Manifest.read(run_dir), read_results(run_dir)))
    typer.echo(f"Wrote {run_dir}")


@app.command()
def train(config: ConfigOption) -> None:
    """Validate a training config, then stop: training is NOT IMPLEMENTED (planned: v0.2, v0.3)."""
    experiment = load_experiment(config)
    if not isinstance(experiment, TrainConfig):
        raise ConfigError(f"{config} is an evaluation config; use 'agentlab eval'")
    typer.echo(f"Config is valid: {config}")
    TRAINERS.get(experiment.trainer.backend)().train(experiment)


@app.command()
def validate(config: ConfigOption) -> None:
    """Check an experiment config without running it."""
    experiment = load_experiment(config)
    typer.echo(f"Config is valid: {config} (kind: {experiment.kind})")


@app.command()
def compare(
    base: Path,
    candidate: Path,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Also write the report here.")] = None,
    allow_mismatch: Annotated[bool, typer.Option(help="Compare runs whose setups differ.")] = False,
) -> None:
    """Compare two runs on the trials both graded."""
    text = render_comparison(
        compare_runs(
            Manifest.read(base),
            read_results(base),
            Manifest.read(candidate),
            read_results(candidate),
            allow_mismatch=allow_mismatch,
        )
    )
    if output is not None:
        output.write_text(text, encoding="utf-8")
    typer.echo(text)


@app.command()
def audit(
    train: Annotated[list[Path], typer.Option(help="Training dataset YAML; repeatable.")],
    evaluation: Annotated[list[Path], typer.Option("--eval", help="Evaluation dataset YAML; repeatable.")],
) -> None:
    """Look for train/evaluation leakage. Only local datasets can be loaded today."""

    def load(paths: list[Path]) -> list[LoadedDataset]:
        configs = [load_dataset_config(p) for p in paths]
        return [DATASETS.get(c.source.type)().load(c) for c in configs]

    report = run_audit(load(train), load(evaluation))
    typer.echo(report.model_dump_json(indent=2))
    if report.leaked:
        raise LeakageError("leakage found")
    if not report.repository_check_complete:
        typer.echo("warning: some tasks declare no repository; the repository check is incomplete", err=True)


def _terminate(signum: int, frame: object) -> None:
    """Unwind instead of dying, so that a runner can stop Harbor and Harbor can remove its containers."""
    raise SystemExit(128 + signum)


def main() -> None:
    for number in (signal.SIGTERM, signal.SIGHUP):
        if signal.getsignal(number) is not signal.SIG_IGN:  # respect nohup
            signal.signal(number, _terminate)
    try:
        app()
    except AgentLabError as exc:
        typer.echo(f"error: {exc}", err=True)
        sys.exit(exc.exit_code)
