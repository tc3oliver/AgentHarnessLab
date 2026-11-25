"""Task images with a harness already installed, so that no trial installs one.

`agentlab images` builds them; a run only uses images that exist. A tag names the content it was built from,
so a changed task, harness version or recipe never picks up a stale image. What a build resolved at build time
(apt, npm dependencies) is fixed by the image id, which every result records.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tomllib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from agent_harness_lab.core.config import HarnessConfig
from agent_harness_lab.dataset.base import TaskRef
from agent_harness_lab.dataset.loaders import hash_task
from agent_harness_lab.errors import ConfigError, RunError

BASE = "python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b"
"""Only used to run the installers; the glibc Node build it fetches works on any newer glibc image."""
NVM_VERSION = "v0.40.2"  # Harbor's
NODE_VERSION = "22.23.5"  # Harbor installs the newest 22.x
_BUILD_TIMEOUT_S = 3600
_ENV = ("PATH", "HOME", "LANG", "TMPDIR", "XDG_RUNTIME_DIR", "SSL_CERT_FILE")


@dataclass(frozen=True)
class _Recipe:
    package: str
    npm_install: str
    """As in Harbor's installer of this agent."""
    version_command: str


_V2 = "/root/.harbor/agents/opencode-v2"
RECIPES = {
    "pi": _Recipe("@earendil-works/pi-coding-agent", "--global --ignore-scripts", "pi"),
    "opencode": _Recipe("opencode-ai", "--global", "opencode"),
    "opencode-v2": _Recipe("@opencode/cli", f"--prefix {_V2}", f"{_V2}/node_modules/.bin/opencode"),
}


def _dockerfile(name: str) -> str:
    return files("agent_harness_lab").joinpath("images", name).read_text(encoding="utf-8")


def _digest(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()[:16]


def _harness_args(harness: HarnessConfig) -> dict[str, str]:
    recipe = RECIPES[harness.name]
    return {
        "BASE": BASE,
        "NVM_VERSION": NVM_VERSION,
        "NODE_VERSION": NODE_VERSION,
        "PACKAGE": f"{recipe.package}@{harness.version}",
        "NPM_INSTALL": recipe.npm_install,
        "VERSION_COMMAND": recipe.version_command,
        "VERSION": harness.version,
    }


def _tag_part(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def harness_tag(harness: HarnessConfig) -> str:
    recipe = _digest(
        _dockerfile("harness.Dockerfile"), *(f"{k}={v}" for k, v in _harness_args(harness).items())
    )
    return f"agentlab/harness-{harness.name}:{_tag_part(harness.version)}-{recipe}"


def _base_tag(task: TaskRef) -> str:
    return f"agentlab/base-{_tag_part(task.task_id)}:{hash_task(task.path / 'environment')[:16]}"


def task_tag(task: TaskRef, harness: HarnessConfig) -> str:
    key = _digest(_base_tag(task), harness_tag(harness), _dockerfile("task.Dockerfile"))
    return f"agentlab/task-{_tag_part(task.task_id)}:{harness.name}-{key}"


def check_task(task: TaskRef) -> None:
    """Refuse what the recipe would get wrong instead of evaluating something else."""
    environment = task.path / "environment"
    if not (environment / "Dockerfile").is_file():
        raise ConfigError(f"task {task.task_id}: prebuilt images need environment/Dockerfile")
    if any(environment.glob("*compose*.y*ml")):
        raise ConfigError(f"task {task.task_id}: prebuilt images do not support compose tasks")
    meta = tomllib.loads((task.path / "task.toml").read_text(encoding="utf-8"))
    if meta.get("environment", {}).get("docker_image"):
        raise ConfigError(f"task {task.task_id}: already uses environment.docker_image")
    if meta.get("agent", {}).get("user") not in {None, "root", 0, "0"}:
        raise ConfigError(f"task {task.task_id}: the agent is not root; harnesses are installed for root")


def stage_task(task: TaskRef, image: str, target: Path) -> Path:
    """Copy a task and name its image. Everything else, including tests and limits, is unchanged."""
    shutil.copytree(task.path, target)
    path = target / "task.toml"
    text = path.read_text(encoding="utf-8")
    before = tomllib.loads(text)
    line = f'docker_image = "{image}"\n'
    if "environment" in before:
        text = re.sub(r"(?m)^\[environment\][^\n]*\n", lambda m: m.group() + line, text, count=1)
    else:
        text = f"{text.rstrip()}\n\n[environment]\n{line}"
    expected = {**before, "environment": {**before.get("environment", {}), "docker_image": image}}
    if tomllib.loads(text) != expected:
        raise ConfigError(f"task {task.task_id}: cannot add docker_image to task.toml")
    path.write_text(text, encoding="utf-8")
    return target


def _docker(args: Sequence[str], *, stdin: str | None = None) -> str:
    env = {k: v for k, v in os.environ.items() if k in _ENV or k.startswith("DOCKER_")}
    try:
        done = subprocess.run(  # noqa: S603
            ["docker", *args],  # noqa: S607
            env=env,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=_BUILD_TIMEOUT_S,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise RunError(f"docker {args[0]} failed: {exc.stderr.strip()[-2000:]}") from exc
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RunError(f"docker {args[0]} failed: {type(exc).__name__}") from exc
    return done.stdout.strip()


def image_id(tag: str) -> str | None:
    """The id of a local image, or None. Never pulls."""
    found = _docker(["image", "ls", "--no-trunc", "--quiet", "--filter", f"reference={tag}"])
    return found.splitlines()[0] if found else None


def required_id(tag: str) -> str:
    found = image_id(tag)
    if found is None:
        raise ConfigError(f"image {tag} does not exist; run 'agentlab images -c <config>' first")
    return found


def prebuilt_image(task: TaskRef, harness: HarnessConfig) -> str:
    """The image id to run a task with. Raise if the task is unsupported or the image was not built."""
    check_task(task)
    return required_id(task_tag(task, harness))


def _build(tag: str, args: dict[str, str], dockerfile: str) -> None:
    flags = [f"--build-arg={k}={v}" for k, v in args.items()]
    _docker(["build", "--quiet", "--pull=false", "-t", tag, *flags, "-"], stdin=dockerfile)


def build_images(harnesses: Sequence[HarnessConfig], tasks: Sequence[TaskRef]) -> Iterator[tuple[str, bool]]:
    """Yield (tag, built). Existing images are kept."""
    for task in tasks:
        check_task(task)
    for harness in harnesses:
        if harness.name not in RECIPES:
            continue
        tag = harness_tag(harness)
        if missing := image_id(tag) is None:
            _build(tag, _harness_args(harness), _dockerfile("harness.Dockerfile"))
        yield tag, missing
    for task in tasks:
        base = _base_tag(task)
        if missing := image_id(base) is None:
            _docker(["build", "--quiet", "-t", base, str(task.path / "environment")])
        yield base, missing
        user = _docker(["image", "inspect", "--format", "{{.Config.User}}", base])
        if user not in {"", "root", "0", "0:0", "root:root"}:
            raise ConfigError(f"task {task.task_id}: the image runs as {user}, not root")
        for harness in harnesses:
            if harness.name not in RECIPES:
                continue
            tag = task_tag(task, harness)
            if missing := image_id(tag) is None:
                _build(tag, {"HARNESS": harness_tag(harness), "TASK": base}, _dockerfile("task.Dockerfile"))
            yield tag, missing
