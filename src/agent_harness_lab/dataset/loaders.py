from __future__ import annotations

import hashlib
import tomllib
from fnmatch import fnmatch
from pathlib import Path

from agent_harness_lab.core.config import DatasetConfig, LocalSource, canonical_hash
from agent_harness_lab.dataset.base import LoadedDataset, TaskRef
from agent_harness_lab.errors import ConfigError, FeatureNotImplementedError

IGNORED = {"__pycache__", ".DS_Store"}


def task_files(task_dir: Path) -> list[Path]:
    files = []
    for path in sorted(task_dir.rglob("*")):
        relative = path.relative_to(task_dir)
        if IGNORED.intersection(relative.parts):
            continue
        if path.is_symlink():
            raise ConfigError(f"task {task_dir.name} contains a symlink: {relative}")
        if path.is_file():
            files.append(path)
    return files


def hash_task(task_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in task_files(task_dir):
        name = path.relative_to(task_dir).as_posix().encode()
        data = path.read_bytes()
        executable = b"x" if path.stat().st_mode & 0o100 else b"-"
        digest.update(b"%d:%s%s%d:" % (len(name), name, executable, len(data)))
        digest.update(data)
    return digest.hexdigest()


def _task_ref(task_dir: Path) -> TaskRef:
    try:
        task = tomllib.loads((task_dir / "task.toml").read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise ConfigError(f"invalid task.toml in {task_dir}: {exc}") from exc
    if "steps" in task:
        raise ConfigError(f"task {task_dir.name}: multi-step tasks are not supported")
    meta = task.get("metadata", {})
    try:
        instruction = (task_dir / "instruction.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"task {task_dir} has no readable instruction.md") from exc
    repository = meta.get("repository")
    return TaskRef(
        task_id=task_dir.name,
        content_hash=hash_task(task_dir),
        instruction_hash=canonical_hash(instruction.lower().split()),
        path=task_dir,
        repository=repository.strip().lower() if isinstance(repository, str) and repository.strip() else None,
    )


class LocalDataset:
    """A directory of Harbor task directories."""

    def load(self, config: DatasetConfig) -> LoadedDataset:
        if not isinstance(config.source, LocalSource):
            raise ConfigError(f"dataset '{config.name}' is not a local source")
        root = Path(config.source.path)
        if not root.is_dir():
            raise ConfigError(f"dataset '{config.name}': no such directory: {root}")
        dirs = sorted(p.parent for p in root.glob("*/task.toml"))
        if config.task_names is not None:
            missing = [n for n in config.task_names if not any(fnmatch(d.name, n) for d in dirs)]
            if missing:
                raise ConfigError(f"dataset '{config.name}': no task matches {missing}")
            dirs = [d for d in dirs if any(fnmatch(d.name, n) for n in config.task_names)]
        dirs = dirs[: config.n_tasks]
        if not dirs:
            raise ConfigError(f"dataset '{config.name}': no tasks found under {root}")
        tasks = tuple(_task_ref(d) for d in dirs)
        revision = canonical_hash([[t.task_id, t.content_hash] for t in tasks])
        return LoadedDataset(config, f"sha256:{revision}", tasks)


class HuggingFaceDataset:
    def load(self, config: DatasetConfig) -> LoadedDataset:
        raise FeatureNotImplementedError(f"Hugging Face download (dataset '{config.name}')", "v0.1")


class GitDataset:
    def load(self, config: DatasetConfig) -> LoadedDataset:
        raise FeatureNotImplementedError(f"git download (dataset '{config.name}')", "v0.1")
