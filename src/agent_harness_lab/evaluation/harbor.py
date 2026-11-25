"""Run a plan with Harbor as a subprocess, one Harbor job per (harness, attempt)."""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from agent_harness_lab.core.config import EvalConfig, HarborRunnerConfig
from agent_harness_lab.core.results import Outcome, TrialResult
from agent_harness_lab.dataset.loaders import hash_task
from agent_harness_lab.errors import ConfigError, RunError
from agent_harness_lab.evaluation.base import TrialSpec
from agent_harness_lab.evaluation.harbor_results import (
    HarborTrial,
    agent_acted,
    agent_finished,
    classify,
    trajectory_counts,
)
from agent_harness_lab.evaluation.runners import price
from agent_harness_lab.harness.base import HarnessAdapter
from agent_harness_lab.inference.openai import OpenAICompatibleBackend, api_key

SUPPORTED_HARBOR = ("0.25.0", "0.27.0")
_MAX_ERROR = 2000
_POLL_S = 1.0
_SETTLE_S = 5.0
"""Harbor may still rewrite a trial's trajectory (secret scrubbing) just after its result.json."""
_STOP_S = 120.0
# Harbor forwards variables it recognises into sandboxes, so it only gets what it needs.
_ENV = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "XDG_RUNTIME_DIR", "XDG_CACHE_HOME", "SSL_CERT_FILE")
_ENV_PREFIXES = ("DOCKER_",)
_NOT_VERIFIED = (
    "AgentAuthenticationError",
    "AgentVersionTooOldError",
    "ApiProviderResourceNotFoundError",
    "ModelNotFoundError",
)
"""Harbor 0.27.0 skips the verifier after these, which it may only have guessed from the agent's output."""


def _harbor(config: EvalConfig) -> HarborRunnerConfig:
    if not isinstance(config.runner, HarborRunnerConfig):
        raise ConfigError("HarborRunner needs runner.type 'harbor'")
    return config.runner


def harbor_env(config: EvalConfig) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in _ENV or k.startswith(_ENV_PREFIXES)}
    env["HARBOR_TELEMETRY"] = "off"
    key = api_key(config.inference)
    if key is not None and config.inference.api_key_env is not None:
        env[config.inference.api_key_env] = key
    return env


def _output(command: Sequence[str], env: dict[str, str]) -> str:
    try:
        out = subprocess.run(  # noqa: S603
            list(command), env=env, capture_output=True, text=True, timeout=60, check=True
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ConfigError(f"cannot run {command[0]!r}: {type(exc).__name__}") from exc
    return out.stdout.strip()


def job_config(
    config: EvalConfig, agent: dict[str, Any], specs: Sequence[TrialSpec], name: str, jobs_dir: Path
) -> dict[str, Any]:
    runner = _harbor(config)
    policy = {} if runner.version == "0.25.0" else {n: {"should_grade": True} for n in _NOT_VERIFIED}
    return {
        **({"override_error_policy": policy} if policy else {}),
        "job_name": name,
        "jobs_dir": str(jobs_dir),
        "n_attempts": 1,
        "n_concurrent_trials": runner.n_concurrent,
        "quiet": True,
        # A retry would hide the cost and the failure of the first try.
        "retry": {"max_retries": 0},
        "environment": {"type": runner.environment},
        "agents": [agent],
        "tasks": [{"path": str(s.task.path.resolve()), "source": s.dataset} for s in specs],
    }


class HarborRunner:
    simulated = False

    def preflight(self, config: EvalConfig, adapters: Mapping[str, HarnessAdapter]) -> dict[str, str]:
        runner = _harbor(config)
        if runner.version not in SUPPORTED_HARBOR:
            raise ConfigError(
                f"Harbor {runner.version} is not supported; tested: {', '.join(SUPPORTED_HARBOR)}"
            )
        for harness in config.harnesses:
            adapter = adapters[harness.name]
            if runner.version not in adapter.harbor_versions:
                raise ConfigError(
                    f"harness '{harness.name}' needs Harbor {' or '.join(sorted(adapter.harbor_versions))}, "
                    f"not {runner.version}"
                )
            adapter.harbor_agent(harness, config.model, config.inference)
        for dataset in config.datasets:
            if dataset.source.type != "local":
                raise ConfigError(f"dataset '{dataset.name}': the Harbor runner needs a local source")
        env = harbor_env(config)
        found = _output([*runner.command, "--version"], env).splitlines()[-1:]
        if found != [runner.version]:
            raise ConfigError(f"runner.version is {runner.version} but the command reports {found}")
        runtime = {"harbor": runner.version}
        if runner.environment == "docker":
            runtime["docker"] = _output(["docker", "version", "--format", "{{.Server.Version}}"], env)
        if config.inference.backend != "none":
            runtime.update(self._probe(config))
        return runtime

    @staticmethod
    def _probe(config: EvalConfig) -> dict[str, str]:
        info = OpenAICompatibleBackend().probe(config.inference)
        served = config.inference.served_model or config.model.id
        if config.model.adapter is not None and served == config.model.id:
            raise ConfigError("inference.served_model must name the adapter, not the base model")
        if served not in info.served_models:
            raise RunError(f"the endpoint does not serve '{served}'")
        runtime = {"served_model": served}
        if info.engine_version is not None:
            runtime["engine"] = info.engine_version
        return runtime

    def run(
        self,
        config: EvalConfig,
        plan: Sequence[TrialSpec],
        adapters: Mapping[str, HarnessAdapter],
        run_dir: Path,
    ) -> Iterator[TrialResult]:
        groups: dict[tuple[str, int], list[TrialSpec]] = {}
        for spec in plan:
            groups.setdefault((spec.harness.name, spec.attempt), []).append(spec)
        for (name, attempt), specs in groups.items():
            agent = adapters[name].harbor_agent(specs[0].harness, config.model, config.inference)
            yield from self._job(
                config, agent, specs, f"{name}-attempt{attempt}", run_dir.resolve() / "harbor"
            )

    def _job(
        self, config: EvalConfig, agent: dict[str, Any], specs: Sequence[TrialSpec], name: str, jobs_dir: Path
    ) -> Iterator[TrialResult]:
        jobs_dir.mkdir(parents=True, exist_ok=True)
        job_file = jobs_dir / f"{name}.config.json"
        body = job_config(config, agent, specs, name, jobs_dir)
        job_file.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
        pending = {s.task.path.resolve(): s for s in specs}
        if len(pending) != len(specs):
            raise ConfigError("two datasets contain the same task directory")
        seen: set[Path] = set()
        log = jobs_dir / f"{name}.log"
        with log.open("w", encoding="utf-8") as out:
            process = subprocess.Popen(  # noqa: S603
                [*_harbor(config).command, "run", "-c", str(job_file), "-y"],
                env=harbor_env(config),
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                while process.poll() is None:
                    yield from self._collect(config, jobs_dir / name, pending, seen, _SETTLE_S)
                    time.sleep(_POLL_S)
                yield from self._collect(config, jobs_dir / name, pending, seen, 0)
            finally:
                _stop(process)
        if len(pending) == len(specs):
            raise RunError(f"Harbor exited with code {process.returncode} and no results; see {log}")
        for spec in pending.values():
            yield _result(spec, Outcome.INFRA_ERROR, "Harbor wrote no result for this trial")
        for spec in specs:
            if hash_task(spec.task.path) != spec.task.content_hash:
                raise RunError(f"task {spec.task.task_id} changed while the run was in progress")
        if config.inference.backend != "none":
            # A dead endpoint turns every later trial into an agent error, which must not count as failure.
            self._probe(config)

    @staticmethod
    def _collect(
        config: EvalConfig,
        job_dir: Path,
        pending: dict[Path, TrialSpec],
        seen: set[Path],
        settle_s: float,
    ) -> Iterator[TrialResult]:
        for path in sorted(job_dir.glob("*/result.json")):
            if path in seen or time.time() - path.stat().st_mtime < settle_s:
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError:
                continue  # still being written
            try:
                trial = HarborTrial.model_validate(data)
            except ValidationError as exc:
                raise RunError(f"unexpected Harbor result {path}: {exc}") from exc
            seen.add(path)
            spec = pending.pop(trial.task_id.path.resolve(), None)
            if spec is None:
                raise RunError(f"Harbor returned an unplanned or repeated trial: {trial.trial_name}")
            yield convert(config, spec, trial, path.parent)


def convert(config: EvalConfig, spec: TrialSpec, trial: HarborTrial, trial_dir: Path) -> TrialResult:
    runner = _harbor(config)
    trajectory = trial_dir / "agent" / "trajectory.json"
    outcome, error = classify(
        trial, runner.reward_key, runner.pass_threshold, finished=agent_finished(trajectory.parent)
    )
    version = trial.observed_version
    if trial.agent_info.name != spec.harness.name:
        raise RunError(f"asked Harbor for '{spec.harness.name}', got '{trial.agent_info.name}'")
    if version is not None and version != spec.harness.version:
        outcome = Outcome.INFRA_ERROR
        error = f"harness version is {version}, not the pinned {spec.harness.version}"
    input_tokens, output_tokens = trial.tokens
    if (
        config.inference.backend != "none"
        and outcome in {Outcome.AGENT_ERROR, Outcome.FAILED}
        and input_tokens is None
        and not trial.step_results  # multi-step trials keep usage and trajectories per step
        and not agent_acted(trajectory)
    ):
        # Typically the sandbox could not reach the endpoint; the harness then just exits with an error.
        error = (
            f"no model usage recorded ({outcome}); {error}"
            if error
            else f"no model usage recorded ({outcome})"
        )
        outcome = Outcome.INFRA_ERROR
    tool_calls, model_calls = trajectory_counts(trajectory)
    return _result(
        spec,
        outcome,
        _redact(config, error, trial_dir),
        harness_version=version,
        rewards=trial.verifier_result.rewards if trial.verifier_result else None,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        tool_calls=tool_calls,
        model_calls=model_calls,
        latency_s=trial.latency_s,
        # Harnesses report 0 for models they have no price for, so only configured prices are used.
        cost_usd=price(config.cost, input_tokens, output_tokens),
    )


def _redact(config: EvalConfig, text: str | None, trial_dir: Path) -> str | None:
    """Error text ends up in results that people publish: drop the key and local paths."""
    key = os.environ.get(config.inference.api_key_env or "")
    if text is None:
        return None
    if key:
        text = text.replace(key, "[redacted]")
    text = text.replace(str(trial_dir), "<trial>").replace(str(Path.home()), "~")
    return re.sub(r"(?i)bearer\s+\S+", "Bearer [redacted]", text)[:_MAX_ERROR]


def _result(spec: TrialSpec, outcome: Outcome, error: str | None, **values: Any) -> TrialResult:
    return TrialResult.model_validate(
        {
            "simulated": False,
            "dataset": spec.dataset,
            "task_id": spec.task.task_id,
            "task_hash": spec.task.content_hash,
            "harness": spec.harness.name,
            "harness_version": None,
            "attempt": spec.attempt,
            "seed": None,
            "outcome": outcome,
            "error": error,
            **values,
        }
    )


def _stop(process: subprocess.Popen[Any]) -> None:
    """Harbor removes its containers on SIGTERM. SIGINT may be ignored when inherited from a script.

    SIGTERM goes to Harbor alone: the same group holds the `docker compose down` that does the removing.
    """
    for stop in (process.terminate, lambda: os.killpg(process.pid, signal.SIGKILL)):
        if process.poll() is not None:
            return
        with suppress(ProcessLookupError):
            stop()
        try:
            process.wait(_STOP_S)
        except subprocess.TimeoutExpired:
            continue
