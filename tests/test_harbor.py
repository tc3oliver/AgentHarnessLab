import json
import os
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from conftest import ROOT, eval_dict
from pydantic import ValidationError
from scripted_endpoint import KEY, MODEL, ScriptedEndpoint

from agent_harness_lab.core.config import EvalConfig, HarnessConfig, InferenceConfig, ModelConfig
from agent_harness_lab.core.experiment import run_evaluation
from agent_harness_lab.core.manifest import Manifest
from agent_harness_lab.core.registry import HARNESSES
from agent_harness_lab.core.results import Outcome
from agent_harness_lab.errors import AgentLabError, ConfigError, RunError
from agent_harness_lab.evaluation import harbor
from agent_harness_lab.evaluation.harbor_results import (
    HarborTrial,
    agent_acted,
    agent_finished,
    classify,
    trajectory_counts,
)
from agent_harness_lab.inference.openai import OpenAICompatibleBackend
from agent_harness_lab.reporting.writers import read_results

FIXTURES = Path(__file__).parent / "fixtures" / "harbor"
VERSIONS = ("0.25.0", "0.27.0")


def load(name: str) -> HarborTrial:
    return HarborTrial.model_validate_json((FIXTURES / name / "result.json").read_text())


# --- recorded results ---


@pytest.mark.parametrize("version", VERSIONS)
@pytest.mark.parametrize(
    ("name", "outcome"),
    [
        ("oracle", Outcome.SOLVED),
        ("nop", Outcome.FAILED),
        ("agent-timeout", Outcome.TIMEOUT),
        ("timeout-but-solved", Outcome.SOLVED),
        ("no-reward", Outcome.VERIFIER_ERROR),
        ("bad-reward", Outcome.VERIFIER_ERROR),
        ("verifier-timeout", Outcome.VERIFIER_ERROR),
        ("build-failure", Outcome.INFRA_ERROR),
        ("pi", Outcome.SOLVED),
        ("opencode", Outcome.SOLVED),
    ],
)
def test_recorded_outcomes(version: str, name: str, outcome: Outcome) -> None:
    got, error = classify(load(f"{version}-{name}"), "reward", 1.0)
    assert got is outcome
    assert bool(error) == (name not in {"oracle", "nop", "pi"})


@pytest.mark.parametrize("kind", ["NonZeroAgentExitCodeError", "ApiRateLimitError", "NetworkConnectionError"])
@pytest.mark.parametrize(("reward", "outcome"), [(1.0, Outcome.SOLVED), (0.0, Outcome.AGENT_ERROR)])
def test_exit_after_a_final_answer_is_graded(kind: str, reward: float, outcome: Outcome) -> None:
    """OpenCode 1.19.6: Harbor searches the whole output of a failed command for provider errors."""
    data = json.loads((FIXTURES / "0.25.0-opencode" / "result.json").read_text())
    data["exception_info"]["exception_type"] = kind
    data["verifier_result"]["rewards"]["reward"] = reward
    trial = HarborTrial.model_validate(data)
    assert agent_finished(FIXTURES / "0.25.0-opencode" / "trajectory.json")
    assert classify(trial, "reward", 1.0, finished=True)[0] is outcome
    if kind != "NonZeroAgentExitCodeError":
        assert classify(trial, "reward", 1.0)[0] is Outcome.INFRA_ERROR
        data["exception_info"]["exception_message"] = "provider said no"
        trial = HarborTrial.model_validate(data)
        assert classify(trial, "reward", 1.0, finished=True)[0] is Outcome.INFRA_ERROR


@pytest.mark.parametrize(
    "change",
    [{"message": ""}, {"tool_calls": [{}]}, {"source": "user"}, {"extra": {"stop_reason": "error"}}],
)
def test_unfinished_trajectories(tmp_path: Path, change: dict[str, Any]) -> None:
    path = tmp_path / "trajectory.json"
    assert not agent_finished(path)
    step = {"source": "agent", "message": "Done."}
    path.write_text(json.dumps({"steps": [step]}))
    assert agent_finished(path)
    path.write_text(json.dumps({"steps": [{**step, **change}]}))
    assert not agent_finished(path)


def test_agent_exit_differs_between_harbor_versions() -> None:
    """0.25.0 does not raise when the oracle script fails; 0.27.0 does."""
    assert classify(load("0.25.0-agent-exit"), "reward", 1.0)[0] is Outcome.FAILED
    assert classify(load("0.27.0-agent-exit"), "reward", 1.0)[0] is Outcome.AGENT_ERROR


def test_recorded_setup_timeout_is_infrastructure() -> None:
    assert classify(load("0.25.0-setup-timeout"), "reward", 1.0)[0] is Outcome.INFRA_ERROR


@pytest.mark.parametrize("name", sorted(p.name for p in FIXTURES.iterdir()))
def test_recorded_fixtures_parse_and_hold_no_local_paths(name: str) -> None:
    load(name)
    for path in (FIXTURES / name).iterdir():
        text = path.read_text()
        assert KEY not in text and "/home/" not in text.replace("/home/user", "")


AGENT_FIXTURES = [f"{v}-{n}" for v in VERSIONS for n in ("pi", "opencode")] + [
    "0.25.0-opencode-1.18.30",
    "0.27.0-opencode-v2",
]


@pytest.mark.parametrize("name", AGENT_FIXTURES)
def test_recorded_agent_metrics(name: str) -> None:
    trial = load(name)
    assert trial.tokens == (200, 20)
    assert trial.latency_s is not None and trial.latency_s > 0
    assert trajectory_counts(FIXTURES / name / "trajectory.json") == (1, 2)


def test_controls_have_no_tokens() -> None:
    assert all(load(f"{v}-oracle").tokens == (None, None) for v in VERSIONS)


def edited(**over: Any) -> HarborTrial:
    data = json.loads((FIXTURES / "0.27.0-nop" / "result.json").read_text())
    return HarborTrial.model_validate({**data, **over})


def exc(name: str) -> dict[str, str]:
    return {"exception_type": name, "exception_message": "m"}


@pytest.mark.parametrize(
    ("name", "outcome"),
    [
        ("ContextWindowExceededError", Outcome.BUDGET_EXHAUSTED),
        ("AgentSafetyRefusalError", Outcome.FAILED),
        ("NonZeroAgentExitCodeError", Outcome.AGENT_ERROR),
        ("ApiConnectionError", Outcome.INFRA_ERROR),
        ("CancelledError", Outcome.INFRA_ERROR),
        ("SomethingNew", Outcome.INFRA_ERROR),
        ("RewardFileEmptyError", Outcome.VERIFIER_ERROR),
    ],
)
def test_other_exceptions(name: str, outcome: Outcome) -> None:
    assert classify(edited(exception_info=exc(name)), "reward", 1.0)[0] is outcome


def test_ungraded_exception_wins_over_a_reward() -> None:
    trial = edited(exception_info=exc("ApiError"), verifier_result={"rewards": {"reward": 1.0}})
    assert classify(trial, "reward", 1.0)[0] is Outcome.INFRA_ERROR


def test_step_exceptions_count() -> None:
    assert (
        classify(edited(step_results=[{"exception_info": exc("ApiError")}]), "reward", 1.0)[0]
        is Outcome.INFRA_ERROR
    )


def test_failed_harness_install_is_infrastructure() -> None:
    trial = edited(
        exception_info=exc("NonZeroAgentExitCodeError"), agent_execution=None, verifier_result=None
    )
    assert classify(trial, "reward", 1.0)[0] is Outcome.INFRA_ERROR


def test_any_ungraded_step_exception_decides() -> None:
    steps = [{"exception_info": exc("AgentTimeoutError")}, {"exception_info": exc("ApiError")}]
    assert classify(edited(step_results=steps), "reward", 1.0)[0] is Outcome.INFRA_ERROR


def test_missing_reward_key_threshold_and_zero_tokens() -> None:
    got, error = classify(edited(verifier_result={"rewards": {"other": 1}}), "reward", 1.0)
    assert got is Outcome.VERIFIER_ERROR and "no 'reward'" in (error or "")
    assert classify(edited(verifier_result=None), "reward", 1.0)[0] is Outcome.VERIFIER_ERROR
    half = edited(verifier_result={"rewards": {"reward": 0.5}})
    assert classify(half, "reward", 0.5)[0] is Outcome.SOLVED
    assert classify(half, "reward", 1.0)[0] is Outcome.FAILED
    assert edited(agent_result={"n_input_tokens": 0, "n_output_tokens": 0}).tokens == (None, None)
    with pytest.raises(ValidationError):
        edited(schema_version=2)


@pytest.mark.parametrize("tool", ["task", "subagent"])
def test_unknown_trajectory_counts(tmp_path: Path, tool: str) -> None:
    path = tmp_path / "t.json"
    assert trajectory_counts(path) == (None, None)
    path.write_text("{")
    assert trajectory_counts(path) == (None, None)
    step: dict[str, Any] = {"source": "agent", "tool_calls": [{"function_name": tool}], "llm_call_count": 1}
    path.write_text(json.dumps({"steps": [step]}))
    assert trajectory_counts(path) == (None, None)
    step["tool_calls"][0]["function_name"] = "bash"
    path.write_text(json.dumps({"steps": [step, {**step, "is_copied_context": True}]}))
    assert trajectory_counts(path) == (1, 1)
    del step["llm_call_count"]
    path.write_text(json.dumps({"steps": [step]}))
    assert trajectory_counts(path) == (1, None)


# --- agent configuration ---

MODEL_CFG = ModelConfig(id=MODEL, revision="a" * 40)
ENDPOINT = InferenceConfig(
    backend="vllm", base_url="http://h/v1", agent_base_url="http://gw/v1", api_key_env="K"
)


def agent(name: str, inference: InferenceConfig = ENDPOINT, **over: Any) -> dict[str, Any]:
    harness = HarnessConfig.model_validate({"name": name, "version": "1.0.0", **over})
    result: dict[str, Any] = HARNESSES.get(name)().harbor_agent(harness, MODEL_CFG, inference)
    return result


def test_agent_configs() -> None:
    assert agent("pi", max_turns=5, timeout_s=9, setup_timeout_s=8) == {
        "name": "pi",
        "model_name": f"openai/{MODEL}",
        "base_url": "http://gw/v1",
        "model_api_key_name": "K",
        "model_api_format": "openai_chat_completions",
        "kwargs": {"version": "1.0.0", "max_turns": 5},
        "override_timeout_sec": 9,
        "override_setup_timeout_sec": 8,
    }
    assert agent("opencode")["model_name"] == f"agentlab/{MODEL}"
    assert agent("opencode-v2", options={"codemode": False})["kwargs"]["codemode"] is False
    assert agent("oracle") == {"name": "oracle"}


def test_rejected_agent_configs() -> None:
    for name in ("opencode", "opencode-v2"):
        with pytest.raises(ConfigError, match="max_turns"):
            agent(name, max_turns=1)
    with pytest.raises(ConfigError, match="unsupported options"):
        agent("pi", options={"prompt_template_path": "x"})
    with pytest.raises(ConfigError, match="api_key_env"):
        agent("pi", ENDPOINT.model_copy(update={"api_key_env": None}))
    with pytest.raises(ConfigError, match="no options"):
        agent("nop", options={"x": 1})


# --- endpoint probe ---


def test_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    with ScriptedEndpoint("127.0.0.1") as endpoint:
        config = InferenceConfig(backend="vllm", base_url=endpoint.url, api_key_env="K")
        with pytest.raises(ConfigError, match="K is not set"):
            OpenAICompatibleBackend().probe(config)
        monkeypatch.setenv("K", KEY)
        info = OpenAICompatibleBackend().probe(config)
        assert info.served_models == (MODEL,) and info.engine_version == "scripted"
        monkeypatch.setenv("K", "wrong-secret")
        with pytest.raises(RunError, match="HTTP 401") as error:
            OpenAICompatibleBackend().probe(config)
        assert "wrong-secret" not in str(error.value)
    with pytest.raises(RunError, match="cannot list models"):
        OpenAICompatibleBackend().probe(config)


# --- the runner, against a fake `harbor` executable ---

FAKE = """#!{python}
import json, os, pathlib, sys, time
mode = pathlib.Path(__file__).with_name("mode").read_text()
if sys.argv[1:] == ["--version"]:
    print("0.25.0"); sys.exit()
assert sys.argv[1] == "run" and sys.argv[2] == "-c" and sys.argv[4] == "-y"
pathlib.Path(__file__).with_name("env.json").write_text(json.dumps(dict(os.environ)))
job = json.loads(pathlib.Path(sys.argv[3]).read_text())
base = json.loads(pathlib.Path({fixture!r}).read_text())
if mode == "crash":
    print("boom"); sys.exit(7)
tasks = job["tasks"][:-1] if mode == "partial" else job["tasks"]
for i, task in enumerate(tasks):
    d = pathlib.Path(job["jobs_dir"], job["job_name"], "t%d" % i)
    d.mkdir(parents=True)
    base.update(trial_name="t%d" % i, task_id=dict(path=task["path"]))
    base["agent_info"] = dict(name=job["agents"][0]["name"], version="9.9" if mode == "drift" else "1.0.0")
    if mode.startswith("no-usage") and mode != "no-usage-solved":
        kind = "AgentTimeoutError" if mode.endswith("timeout") else "NonZeroAgentExitCodeError"
        base["exception_info"] = dict(exception_type=kind, exception_message="m")
        base["verifier_result"] = dict(rewards=dict(reward=0.0))
    if mode == "no-usage-steps":
        base.update(step_results=[dict()], agent_result=None)
    if mode == "no-usage-acted":
        (d / "agent").mkdir()
        step = dict(source="agent", message="hi")
        (d / "agent" / "trajectory.json").write_text(json.dumps(dict(steps=[step])))
    if mode == "stranger":
        base["task_id"] = dict(path="/elsewhere")
    if mode == "touch":
        pathlib.Path(task["path"], "instruction.md").write_text("changed")
    if mode == "leak":
        msg = "x" * 1980 + os.environ["K"] + " "
        msg = ("Bearer abc " if i else msg) + os.environ["K"] + " at " + str(d) + " in " + os.environ["HOME"]
        base["exception_info"] = dict(exception_type="ApiError", exception_message=msg)
    (d / "result.json").write_text("{{" if mode == "garbage" else json.dumps(base))
if mode == "hang":
    import signal
    def stop(*_):
        pathlib.Path(__file__).with_name("interrupted").write_text("")
        sys.exit(1)
    signal.signal(signal.SIGTERM, stop)
    pathlib.Path(__file__).with_name("started").write_text("")
    time.sleep(60)
"""


@pytest.fixture
def fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(harbor, "_POLL_S", 0.02)
    monkeypatch.setattr(harbor, "_SETTLE_S", 0)
    home = tmp_path / "bin"
    home.mkdir()
    script = home / "harbor"
    fixture = str(FIXTURES / "0.27.0-oracle" / "result.json")
    script.write_text(FAKE.format(python=sys.executable, fixture=fixture))
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    (home / "mode").write_text("ok")
    return home


def harbor_dict(tasks: Path, out: Path, fake: Path, **over: Any) -> dict[str, Any]:
    return eval_dict(
        tasks,
        out,
        **{
            "model": {"id": "none"},
            "inference": {"backend": "none"},
            "harnesses": [{"name": "oracle", "version": "1.0.0"}],
            "runner": {
                "type": "harbor",
                "version": "0.25.0",
                "environment": "fake",
                "command": [str(fake / "harbor")],
            },
            **over,
        },
    )


def run(tasks: Path, tmp_path: Path, fake: Path, mode: str = "ok", **over: Any) -> Path:
    (fake / "mode").write_text(mode)
    return run_evaluation(EvalConfig.model_validate(harbor_dict(tasks, tmp_path / "runs", fake, **over)))


def test_run(tasks: Path, tmp_path: Path, fake: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("UNRELATED_SECRET", "x")
    run_dir = run(tasks, tmp_path, fake, n_attempts=2)
    results = read_results(run_dir)
    assert len(results) == 12 and {r.outcome for r in results} == {Outcome.SOLVED}
    assert {r.attempt for r in results} == {1, 2}
    assert all(not r.simulated and r.seed is None and r.tool_calls is None for r in results)
    manifest = Manifest.read(run_dir)
    assert manifest.runtime == {"harbor": "0.25.0"} and not manifest.simulated
    assert manifest.harnesses[0].observed_versions == ["1.0.0"]
    job = json.loads((run_dir / "harbor/oracle-attempt1.config.json").read_text())
    assert job["retry"] == {"max_retries": 0} and job["n_attempts"] == 1
    env = json.loads((fake / "env.json").read_text())
    assert "UNRELATED_SECRET" not in env and env["HARBOR_TELEMETRY"] == "off"
    with pytest.raises(RunError, match="other files"):
        run_evaluation(manifest.config, overwrite=True)


def test_partial_results_are_infrastructure_errors(tasks: Path, tmp_path: Path, fake: Path) -> None:
    results = read_results(run(tasks, tmp_path, fake, "partial"))
    missing = [r for r in results if r.outcome is Outcome.INFRA_ERROR]
    assert len(results) == 6 and len(missing) == 1 and "no result" in (missing[0].error or "")


def test_version_drift_is_never_graded(tasks: Path, tmp_path: Path, fake: Path) -> None:
    results = read_results(run(tasks, tmp_path, fake, "drift"))
    assert {r.outcome for r in results} == {Outcome.INFRA_ERROR}
    assert all("9.9" in (r.error or "") for r in results)


@pytest.mark.parametrize(
    ("mode", "message"),
    [("crash", "code 7"), ("garbage", "no results"), ("stranger", "unplanned"), ("touch", "changed while")],
)
def test_broken_runs(tasks: Path, tmp_path: Path, fake: Path, mode: str, message: str) -> None:
    with pytest.raises(RunError, match=message):
        run(tasks, tmp_path, fake, mode)
    assert Manifest.read(tmp_path / "runs/base").status == "failed"


def test_endpoint_runs_redact_errors(
    tasks: Path, tmp_path: Path, fake: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("K", KEY)
    with ScriptedEndpoint("127.0.0.1") as endpoint:
        over = {
            "model": {"id": MODEL, "revision": "a" * 40},
            "inference": {"backend": "vllm", "base_url": endpoint.url, "api_key_env": "K"},
            "harnesses": [{"name": "pi", "version": "1.0.0"}],
        }
        run_dir = run(tasks, tmp_path, fake, "leak", **over)
        manifest = Manifest.read(run_dir)
        assert manifest.runtime["served_model"] == MODEL and manifest.runtime["engine"] == "scripted"
        for result in read_results(run_dir):
            assert result.outcome is Outcome.INFRA_ERROR and result.error is not None
            assert KEY not in result.error and "abc" not in result.error
            assert KEY[:8] not in result.error and str(Path.home()) not in result.error
        assert any("<trial>" in (r.error or "") for r in read_results(run_dir))
        assert KEY not in (run_dir / "manifest.json").read_text()
        over["model"] = {"id": "other", "revision": "a" * 40}
        with pytest.raises(RunError, match="does not serve"):
            run(tasks, tmp_path / "x", fake, **over)


@pytest.mark.parametrize(
    ("over", "message"),
    [
        ({"runner": {"version": "0.27.0"}}, "command reports"),
        ({"runner": {"version": "0.26.0"}}, "not supported"),
        ({"runner": {"command": ["/nonexistent/harbor"]}}, "cannot run"),
        ({"harnesses": [{"name": "opencode-v2", "version": "2.2.7"}]}, "needs Harbor 0.27.0"),
    ],
)
def test_preflight(tasks: Path, tmp_path: Path, fake: Path, over: dict[str, Any], message: str) -> None:
    data = harbor_dict(tasks, tmp_path / "runs", fake)
    if "harnesses" in over:
        data["harnesses"] = over["harnesses"]
        data["model"] = {"id": "m", "revision": "a" * 40}
        data["inference"] = {"backend": "vllm", "base_url": "http://127.0.0.1:1/v1", "api_key_env": "K"}
    data["runner"] = {**data["runner"], **over.get("runner", {})}
    with pytest.raises(AgentLabError, match=message):
        run_evaluation(EvalConfig.model_validate(data))
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize(
    "over",
    [
        {"harnesses": [{"name": "oracle", "version": "1.0.0"}, {"name": "pi", "version": "1.0.0"}]},
        {"harnesses": [{"name": "pi", "version": "1.0.0"}]},
    ],
)
def test_control_harnesses_do_not_mix(tasks: Path, tmp_path: Path, fake: Path, over: dict[str, Any]) -> None:
    with pytest.raises(ValidationError, match="oracle or nop"):
        EvalConfig.model_validate(harbor_dict(tasks, tmp_path, fake, **over))


@pytest.mark.parametrize("number", [signal.SIGTERM, signal.SIGHUP])
def test_signals_stop_harbor(tasks: Path, tmp_path: Path, fake: Path, number: signal.Signals) -> None:
    (fake / "mode").write_text("hang")
    config = tmp_path / "c.yaml"
    config.write_text(json.dumps(harbor_dict(tasks, tmp_path / "runs", fake)))
    command = [sys.executable, "-m", "agent_harness_lab", "eval", "-c", str(config)]
    previous = signal.signal(number, signal.SIG_DFL)  # a child of nohup inherits SIG_IGN
    try:
        process = subprocess.Popen(command)  # noqa: S603
    finally:
        signal.signal(number, previous)
    deadline = time.monotonic() + 30
    while not (fake / "started").exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    process.send_signal(number)
    assert process.wait(30) == 128 + number
    assert (fake / "interrupted").exists()
    assert Manifest.read(tmp_path / "runs/base").status == "failed"


def test_results_settle_before_they_are_read(
    tasks: Path, tmp_path: Path, fake: Path, config: EvalConfig
) -> None:
    job = tmp_path / "job"
    (job / "t").mkdir(parents=True)
    collect = harbor.HarborRunner._collect
    seen: set[Path] = set()
    (job / "t" / "result.json").write_text(json.dumps({"not": "harbor"}))
    assert list(collect(config, job, {}, seen, 3600)) == []
    with pytest.raises(RunError, match="unexpected Harbor result"):
        list(collect(config, job, {}, seen, 0))


def test_agent_activity_without_usage_stays_graded(tmp_path: Path) -> None:
    path = tmp_path / "t.json"
    assert not agent_acted(path)
    path.write_text(json.dumps({"steps": [{"source": "user", "message": "x"}, {"source": "agent"}]}))
    assert not agent_acted(path)
    path.write_text(json.dumps({"steps": [{"source": "agent", "message": "x"}]}))
    assert agent_acted(path)


@pytest.mark.parametrize(
    "mode", ["no-usage", "no-usage-solved", "no-usage-acted", "no-usage-timeout", "no-usage-steps"]
)
def test_unsolved_trials_without_model_usage_are_infrastructure(
    tasks: Path, tmp_path: Path, fake: Path, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    monkeypatch.setenv("K", KEY)
    with ScriptedEndpoint("127.0.0.1") as endpoint:
        run_dir = run(
            tasks,
            tmp_path,
            fake,
            mode,
            model={"id": MODEL, "revision": "a" * 40},
            inference={"backend": "vllm", "base_url": endpoint.url, "api_key_env": "K"},
            harnesses=[{"name": "opencode", "version": "1.0.0"}],
        )
    [outcome] = {r.outcome for r in read_results(run_dir)}
    assert (
        outcome
        is {
            "no-usage": Outcome.INFRA_ERROR,
            "no-usage-solved": Outcome.SOLVED,
            "no-usage-acted": Outcome.AGENT_ERROR,
            "no-usage-timeout": Outcome.TIMEOUT,
            "no-usage-steps": Outcome.AGENT_ERROR,
        }[mode]
    )


# --- real Harbor in Docker: uv run --extra harbor pytest -m docker ---

HARBOR = os.environ.get("AGENTLAB_HARBOR", "harbor")
HARBOR_VERSION = os.environ.get("AGENTLAB_HARBOR_VERSION", "0.25.0")
GATEWAY = os.environ.get("AGENTLAB_DOCKER_GATEWAY", "172.17.0.1")


def real(out: Path, **over: Any) -> Path:
    data = eval_dict(
        ROOT / "examples/smoke_tasks/tasks",
        out,
        **{
            "model": {"id": "none"},
            "inference": {"backend": "none"},
            "runner": {
                "type": "harbor",
                "version": HARBOR_VERSION,
                "n_concurrent": 4,
                "command": [HARBOR],
            },
            **over,
        },
    )
    return run_evaluation(EvalConfig.model_validate(data))


@pytest.mark.docker
@pytest.mark.parametrize(("name", "solved"), [("oracle", 12), ("nop", 0)])
def test_smoke_controls(tmp_path: Path, name: str, solved: int) -> None:
    results = read_results(real(tmp_path, harnesses=[{"name": name, "version": "1.0.0"}]))
    assert len(results) == 12 and all(r.outcome.graded for r in results)
    assert sum(r.outcome is Outcome.SOLVED for r in results) == solved


FIX_MEDIAN = """python3 - <<'P'
open('/app/stats.py', 'w').write('''import statistics
def median(xs):
    if not xs: raise ValueError
    return statistics.median(xs)
def mean(xs):
    return sum(xs) / len(xs)
''')
P"""

AGENTS = [("pi", "1.6.0"), ("opencode", "1.18.30")]
if HARBOR_VERSION == "0.27.0":
    AGENTS += [("pi", "1.5.2"), ("opencode-v2", "2.2.7")]


@pytest.mark.docker
@pytest.mark.parametrize(("name", "version"), AGENTS)
def test_real_harness_against_a_scripted_endpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, version: str
) -> None:
    monkeypatch.setenv("K", KEY)
    with ScriptedEndpoint(GATEWAY, FIX_MEDIAN) as endpoint:
        run_dir = real(
            tmp_path,
            model={"id": MODEL, "revision": "a" * 40},
            inference={"backend": "vllm", "base_url": endpoint.url, "api_key_env": "K"},
            harnesses=[{"name": name, "version": version, "timeout_s": 300, "setup_timeout_s": 1800}],
            datasets=[
                {
                    "name": "smoke",
                    "source": {"type": "local", "path": str(ROOT / "examples/smoke_tasks/tasks")},
                    "split": "smoke",
                    "task_names": ["ahl-fix-median"],
                }
            ],
        )
    [result] = read_results(run_dir)
    assert result.outcome is Outcome.SOLVED, result.error
    assert result.harness_version == version
    assert result.tool_calls == 1 and result.model_calls == 2
    assert (result.input_tokens, result.output_tokens) == (200, 20)
    assert {r["path"] for r in endpoint.requests} == {"/v1/chat/completions"}
