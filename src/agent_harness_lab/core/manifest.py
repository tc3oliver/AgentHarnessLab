"""The experiment manifest: what is needed to say whether two runs are comparable, and to repeat one."""

from __future__ import annotations

import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from agent_harness_lab import __version__
from agent_harness_lab.core.config import EvalConfig, canonical_hash
from agent_harness_lab.dataset.base import LoadedDataset, Provenance
from agent_harness_lab.errors import RunError

MANIFEST_FILE = "manifest.json"
_PACKAGES = ("harbor", "openenv", "trl", "peft", "transformers", "torch", "vllm")


class CodeInfo(BaseModel):
    package_version: str
    commit: str | None
    dirty: bool | None


class DatasetInfo(BaseModel):
    name: str
    split: str
    revision: str
    license: str | None
    n_tasks: int
    tasks_hash: str
    version: str | None = None
    source_type: str | None = None
    source: str | None = None
    source_revision: str | None = None
    source_path: str | None = None
    redistributable: bool | None = None


class HarnessInfo(BaseModel):
    name: str
    requested_version: str
    observed_versions: list[str] = []


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    name: str
    status: Literal["running", "completed", "failed"]
    simulated: bool
    created_at: datetime
    finished_at: datetime | None = None
    error: str | None = None
    n_planned: int
    n_recorded: int = 0
    seed: int
    config: EvalConfig
    config_hash: str
    code: CodeInfo
    datasets: list[DatasetInfo]
    harnesses: list[HarnessInfo]
    python: str
    platform: str
    packages: dict[str, str]
    runtime: dict[str, str]
    """Versions reported by the runner at preflight: Harbor, Docker, served model, engine."""

    def comparability(self) -> dict[str, Any]:
        """Everything that must match between two arms. Model and adapter are the variable under test."""
        c = self.config
        return {
            "simulated": self.simulated,
            "package_version": self.code.package_version,
            "seed": self.seed,
            "n_attempts": c.n_attempts,
            "datasets": sorted(
                (d.name, d.version or "", d.split, d.revision, d.tasks_hash) for d in self.datasets
            ),
            "harnesses": [h.model_dump() for h in sorted(c.harnesses, key=lambda h: h.name)],
            "observed_harness_versions": sorted((h.name, tuple(h.observed_versions)) for h in self.harnesses),
            "sampling": c.inference.sampling.model_dump(),
            "server_args": c.inference.server_args,
            "runner": None if self.simulated else c.runner.model_dump(),
            "cost": c.cost.model_dump() if c.cost else None,
            "hardware": c.hardware.model_dump(),
            "packages": self.packages,
            "runtime": {k: v for k, v in self.runtime.items() if k != "served_model"},
        }

    def write(self, run_dir: Path) -> None:
        tmp = run_dir / f"{MANIFEST_FILE}.tmp"
        tmp.write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")
        tmp.replace(run_dir / MANIFEST_FILE)

    @classmethod
    def read(cls, run_dir: Path) -> Manifest:
        path = run_dir / MANIFEST_FILE
        try:
            return cls.model_validate_json(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise RunError(f"{run_dir} is not a run directory: cannot read {MANIFEST_FILE}") from exc
        except ValidationError as exc:
            raise RunError(f"invalid manifest {path}: {exc}") from exc


def _git(*args: str) -> str | None:
    """Query the checkout that contains this package; installed wheels have no commit."""
    here = Path(__file__).resolve().parent
    try:
        out = subprocess.run(  # noqa: S603
            ["git", "-C", str(here), *args],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def code_info() -> CodeInfo:
    # A wheel in some other project's .venv would otherwise report that project's commit.
    tracked = _git("ls-files", "--error-unmatch", Path(__file__).name)
    if tracked is None:
        return CodeInfo(package_version=__version__, commit=None, dirty=None)
    status = _git("status", "--porcelain")
    return CodeInfo(
        package_version=__version__,
        commit=_git("rev-parse", "HEAD"),
        dirty=None if status is None else bool(status),
    )


def installed_packages() -> dict[str, str]:
    found = {}
    for name in _PACKAGES:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            continue
    return found


def _provenance(p: Provenance) -> dict[str, Any]:
    return {
        "source_type": p.source_type,
        "source": p.location,
        "source_revision": p.revision,
        "source_path": p.path,
        "redistributable": p.redistributable,
    }


def new_manifest(
    config: EvalConfig,
    datasets: list[LoadedDataset],
    n_planned: int,
    simulated: bool,
    runtime: dict[str, str],
) -> Manifest:
    return Manifest(
        name=config.name,
        status="running",
        simulated=simulated,
        created_at=datetime.now(UTC),
        n_planned=n_planned,
        seed=config.seed,
        config=config,
        config_hash=canonical_hash(config.model_dump(mode="json")),
        code=code_info(),
        datasets=[
            DatasetInfo(
                name=d.config.name,
                split=d.config.split,
                revision=d.revision,
                license=d.config.license,
                n_tasks=len(d.tasks),
                tasks_hash=canonical_hash([[t.task_id, t.content_hash] for t in d.tasks]),
                version=d.config.version,
                **({} if d.provenance is None else _provenance(d.provenance)),
            )
            for d in datasets
        ],
        harnesses=[HarnessInfo(name=h.name, requested_version=h.version) for h in config.harnesses],
        python=platform.python_version(),
        platform=f"{platform.system()}-{platform.machine()}",
        packages=installed_packages(),
        runtime=runtime,
    )
