import importlib
import json
import sys
import tomllib
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest
from conftest import ROOT, make_task
from scripted_endpoint import KEY, MODEL, ScriptedEndpoint
from test_harbor import fake, harbor_dict  # noqa: F401
from typer.testing import CliRunner

from agent_harness_lab.cli import app
from agent_harness_lab.core.config import EvalConfig, HarnessConfig
from agent_harness_lab.core.experiment import run_evaluation
from agent_harness_lab.core.manifest import Manifest
from agent_harness_lab.core.results import Outcome
from agent_harness_lab.dataset.base import TaskRef
from agent_harness_lab.dataset.loaders import _task_ref
from agent_harness_lab.errors import ConfigError, RunError
from agent_harness_lab.evaluation import harbor, images
from agent_harness_lab.reporting.writers import read_results


def harness(name: str = "pi", version: str = "1.0.0") -> HarnessConfig:
    return HarnessConfig(name=name, version=version)


def task(root: Path, name: str = "t", toml: str = "", dockerfile: bool = True) -> TaskRef:
    path = make_task(root, name)
    with (path / "task.toml").open("a") as file:
        file.write(toml)
    (path / "environment").mkdir()
    if dockerfile:
        (path / "environment" / "Dockerfile").write_text("FROM x\n")
    return _task_ref(path)


def test_tags_name_their_content(tmp_path: Path) -> None:
    first = task(tmp_path, "My_Task")
    tag = images.task_tag(first, harness())
    assert tag.startswith("agentlab/task-my-task:pi-") and tag == images.task_tag(first, harness())
    assert tag != images.task_tag(first, harness(version="1.0.1"))
    assert tag != images.task_tag(first, harness("opencode"))
    (first.path / "environment" / "Dockerfile").write_text("FROM y\n")
    assert tag != images.task_tag(first, harness())


def test_tests_do_not_change_the_image(tmp_path: Path) -> None:
    ref = task(tmp_path)
    tag = images.task_tag(ref, harness())
    (ref.path / "tests" / "test.sh").write_text("exit 1\n")
    assert tag == images.task_tag(ref, harness())


@pytest.mark.parametrize(
    "toml", ["", "[environment]\ncpus = 1\n[agent]\ntimeout_sec = 5\n", "[environment] # note\ncpus = 1\n"]
)
def test_staging_only_adds_the_image(tmp_path: Path, toml: str) -> None:
    ref = task(tmp_path, toml=toml)
    before = {p: p.read_bytes() for p in ref.path.rglob("*") if p.is_file()}
    copy = images.stage_task(ref, "sha256:abc", tmp_path / "out" / "t")
    assert before == {p: p.read_bytes() for p in ref.path.rglob("*") if p.is_file()}
    new, old = (tomllib.loads((d / "task.toml").read_text()) for d in (copy, ref.path))
    assert new["environment"].pop("docker_image") == "sha256:abc"
    assert new == {"environment": {}, **old}
    for path, data in before.items():
        if path.name != "task.toml":
            assert (copy / path.relative_to(ref.path)).read_bytes() == data


def test_staging_refuses_toml_it_cannot_edit(tmp_path: Path) -> None:
    ref = task(tmp_path, toml="[environment.env]\nA = 'b'\n")
    with pytest.raises(ConfigError, match="cannot add docker_image"):
        images.stage_task(ref, "x", tmp_path / "out")


@pytest.mark.parametrize(
    ("toml", "message"),
    [
        ('[environment]\ndocker_image = "x"\n', "already uses"),
        ('[agent]\nuser = "dev"\n', "not root"),
    ],
)
def test_unsupported_tasks(tmp_path: Path, toml: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        images.check_task(task(tmp_path, toml=toml))


def test_unsupported_environments(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Dockerfile"):
        images.check_task(task(tmp_path, "a", dockerfile=False))
    ref = task(tmp_path, "b")
    (ref.path / "environment" / "docker-compose.yaml").write_text("services: {}\n")
    with pytest.raises(ConfigError, match="compose"):
        images.check_task(ref)


def test_build_order_and_reuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    have: set[str] = set()
    calls: list[list[str]] = []

    def docker(args: list[str], *, stdin: str | None = None) -> str:
        if args[0] == "build":
            calls.append(args)
            have.add(args[args.index("-t") + 1])
        return ""

    monkeypatch.setattr(images, "_docker", docker)
    monkeypatch.setattr(images, "image_id", lambda tag: "sha256:1" if tag in have else None)
    ref = task(tmp_path)
    arms = [harness(), harness("opencode-v2", "2.0.0"), harness("oracle")]
    first = list(images.build_images(arms, [ref]))
    assert [built for _, built in first] == [True] * 5
    assert not any(a.split("=")[0] == "K" or "secret" in a for c in calls for a in c)
    assert list(images.build_images(arms, [ref])) == [(tag, False) for tag, _ in first]


def test_non_root_images_are_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(images, "image_id", lambda tag: "sha256:1")
    monkeypatch.setattr(images, "_docker", lambda *a, **k: "node")
    with pytest.raises(ConfigError, match="runs as node"):
        list(images.build_images([harness()], [task(tmp_path)]))


def test_docker_errors(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(RunError, match="docker image failed"):
        images.image_id("x")


def test_prebuilt_agents(config: EvalConfig) -> None:
    agent = {"name": "pi", "kwargs": {"version": "1.0.0"}}
    assert harbor.prebuilt_agent(agent, "0.27.0")["kwargs"] == {"version": "1.0.0", "skip_install": True}
    old = harbor.prebuilt_agent(agent, "0.25.0")
    assert old["name"] is None and old["import_path"] == "agentlab_prebuilt:PrebuiltPi"
    assert agent == {"name": "pi", "kwargs": {"version": "1.0.0"}}


@pytest.fixture
def endpoint(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("K", KEY)
    with ScriptedEndpoint("127.0.0.1") as server:
        yield server


def evaluate(root: Path, out: Path, fake: Path, url: str, **over: Any) -> Path:  # noqa: F811
    return run_evaluation(
        EvalConfig.model_validate(
            harbor_dict(
                root,
                out,
                fake,
                model={"id": MODEL, "revision": "a" * 40},
                inference={"backend": "vllm", "base_url": url, "api_key_env": "K"},
                harnesses=[{"name": "pi", "version": over.pop("version", "1.0.0")}],
                runner={
                    "type": "harbor",
                    "version": "0.25.0",
                    "command": [str(fake / "harbor")],
                    "prebuilt": True,
                    **over,
                },
            )
        )
    )


def test_run_uses_pinned_images(
    tmp_path: Path,
    fake: Path,  # noqa: F811
    endpoint: ScriptedEndpoint,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "tasks"
    for name in ("t0", "t1"):
        task(root, name)
    monkeypatch.setattr(harbor, "_output", fake_docker(harbor._output))
    monkeypatch.setattr(images, "image_id", lambda tag: f"sha256:{tag}")
    run_dir = evaluate(root, tmp_path / "runs", fake, endpoint.url)
    results = read_results(run_dir)
    assert {r.outcome for r in results} == {Outcome.SOLVED}
    assert all(r.image and r.image.startswith("sha256:agentlab/task-") for r in results)
    assert all(r.setup_s is not None for r in results)
    assert Manifest.read(run_dir).runtime["image.pi"].startswith("sha256:agentlab/harness-pi:1-0-0")
    job = json.loads((run_dir / "harbor/pi-attempt1.config.json").read_text())
    assert job["agents"][0]["import_path"] == "agentlab_prebuilt:PrebuiltPi"
    for entry in job["tasks"]:
        toml = tomllib.loads(Path(entry["path"], "task.toml").read_text())
        assert toml["environment"]["docker_image"].startswith("sha256:")
    path = json.loads((fake / "env.json").read_text())["PYTHONPATH"]
    assert (Path(path) / "agentlab_prebuilt.py").is_file()

    (fake / "mode").write_text("unknown-version")
    unknown = read_results(evaluate(root, tmp_path / "runs2", fake, endpoint.url))
    assert {r.outcome for r in unknown} == {Outcome.INFRA_ERROR}
    assert all("cannot read the harness version" in (r.error or "") for r in unknown)


def fake_docker(real: Any) -> Any:
    return lambda command, env: "29" if command[0] == "docker" else real(command, env)


def test_missing_images_stop_before_anything_is_written(
    tmp_path: Path,
    fake: Path,  # noqa: F811
    endpoint: ScriptedEndpoint,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task(tmp_path / "tasks", "t0")
    monkeypatch.setattr(harbor, "_output", fake_docker(harbor._output))
    monkeypatch.setattr(images, "image_id", lambda tag: None)
    with pytest.raises(ConfigError, match="agentlab images"):
        evaluate(tmp_path / "tasks", tmp_path / "runs", fake, endpoint.url)
    assert not (tmp_path / "runs").exists()
    with pytest.raises(ConfigError, match="docker environment"):
        evaluate(tmp_path / "tasks", tmp_path / "runs", fake, endpoint.url, environment="other")


def test_images_command(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(images, "image_id", lambda tag: "sha256:1")
    monkeypatch.setattr(images, "_docker", lambda *a, **k: "")
    monkeypatch.chdir(ROOT)
    done = CliRunner().invoke(app, ["images", "-c", "configs/experiments/baseline.yaml"])
    assert done.exit_code == 0 and "exists agentlab/harness-pi:" in done.output


# --- the Harbor 0.25.0 plugin, against stand-ins for Harbor's classes ---


@pytest.mark.parametrize(("out", "ok"), [("1.0.0\n", True), ("1.0.1\n", False), ("", False)])
@pytest.mark.parametrize("name", ["PrebuiltPi", "PrebuiltOpenCode"])
def test_plugin_checks_the_version(monkeypatch: pytest.MonkeyPatch, name: str, out: str, ok: bool) -> None:
    import asyncio

    class Agent:
        _version = "1.0.0"

        def get_version_command(self) -> str:
            return "x --version"

        def parse_version(self, text: str) -> str:
            return text.strip()

        async def install(self, environment: Any) -> None:
            raise AssertionError("installed")

    for module, attr in (("pi", "Pi"), ("opencode", "OpenCode")):
        stub = ModuleType(module)
        setattr(stub, attr, Agent)
        monkeypatch.setitem(sys.modules, f"harbor.agents.installed.{module}", stub)
    for parent in ("harbor", "harbor.agents", "harbor.agents.installed"):
        monkeypatch.setitem(sys.modules, parent, ModuleType(parent))
    monkeypatch.syspath_prepend(str(harbor._PLUGIN_DIR))
    monkeypatch.delitem(sys.modules, "agentlab_prebuilt", raising=False)
    plugin = importlib.import_module("agentlab_prebuilt")

    class Environment:
        async def exec(self, command: str) -> Any:
            return SimpleNamespace(return_code=0, stdout=out)

    install = getattr(plugin, name)().install(Environment())
    if ok:
        asyncio.run(install)
    else:
        with pytest.raises(RuntimeError, match=r"not 1\.0\.0"):
            asyncio.run(install)
    monkeypatch.delitem(sys.modules, "agentlab_prebuilt")
