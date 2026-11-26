from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tomllib
import uuid
from collections.abc import Mapping
from fnmatch import fnmatch
from pathlib import Path

from agent_harness_lab.core.config import (
    DatasetConfig,
    GitSource,
    HuggingFaceSource,
    LocalSource,
    canonical_hash,
)
from agent_harness_lab.dataset.base import LoadedDataset, Provenance, TaskRef
from agent_harness_lab.errors import ConfigError

DATASET_MANIFEST = "dataset-manifest.json"
""" Optional file at the dataset root: {"tasks": {task_id: content_hash}}. """

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


COMPLETE_MARKER = "agentlab-complete.json"
"""Written under `.cache` after a download was verified: {file: etag} for every file of the selection."""


def _etag_matches(path: Path, etag: str) -> bool:
    """The Hub's etag is the git blob sha1 of a regular file and the sha256 of an LFS file."""
    wanted = etag.removeprefix("W/").strip('"')
    data = path.read_bytes()
    blob = hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()
    return wanted in {blob, hashlib.sha256(data).hexdigest()}


def _cache_root(cache: Path | None) -> Path:
    if cache is not None:
        return cache
    env = os.environ.get("AGENTLAB_CACHE")
    return Path(env) if env else Path.home() / ".cache" / "agent-harness-lab" / "datasets"


def _is_offline(offline: bool | None) -> bool:
    if offline is not None:
        return offline
    return os.environ.get("AGENTLAB_OFFLINE", "").lower() in {"1", "true", "yes"}


def _require_license(config: DatasetConfig) -> None:
    if config.license is None:
        raise ConfigError(
            f"dataset '{config.name}': refusing to download a dataset with an unknown licence; "
            "set `license` after checking the publisher's terms (docs/DATASETS.md)"
        )


def tasks_hash(tasks: tuple[TaskRef, ...]) -> str:
    return "sha256:" + canonical_hash([[t.task_id, t.content_hash] for t in tasks])


def _contained(config: DatasetConfig, path: Path, boundary: Path) -> None:
    """`path` must be real and inside `boundary`: no symlink on the way, and no way out."""
    base = boundary.resolve()
    try:
        parts = path.relative_to(boundary).parts
    except ValueError:
        parts = ()
    current = boundary
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ConfigError(f"dataset '{config.name}': {current} is a symlink")
    if not path.resolve().is_relative_to(base):
        raise ConfigError(f"dataset '{config.name}': {path} is outside {boundary}")


def _select(config: DatasetConfig, root: Path, boundary: Path) -> tuple[TaskRef, ...]:
    if not root.is_dir():
        raise ConfigError(f"dataset '{config.name}': no such directory: {root}")
    _contained(config, root, boundary)
    dirs = sorted(p.parent for p in root.glob("*/task.toml"))
    for d in dirs:
        _contained(config, d, boundary)
    if config.task_names is not None:
        missing = [n for n in config.task_names if not any(fnmatch(d.name, n) for d in dirs)]
        if missing:
            raise ConfigError(f"dataset '{config.name}': no task matches {missing}")
        dirs = [d for d in dirs if any(fnmatch(d.name, n) for n in config.task_names)]
    dirs = dirs[: config.n_tasks]
    if not dirs:
        raise ConfigError(f"dataset '{config.name}': no tasks found under {root}")
    return tuple(_task_ref(d) for d in dirs)


def _verify(config: DatasetConfig, root: Path, tasks: tuple[TaskRef, ...]) -> None:
    """Check the loaded tasks against `tasks_hash` and the optional `dataset-manifest.json`."""
    if config.tasks_hash is not None and tasks_hash(tasks) != config.tasks_hash:
        raise ConfigError(
            f"dataset '{config.name}': task-list hash is {tasks_hash(tasks)}, config pins {config.tasks_hash}"
        )
    file = root / DATASET_MANIFEST
    if not file.is_file():
        return
    try:
        listed = json.loads(file.read_text(encoding="utf-8"))["tasks"]
        if not isinstance(listed, dict) or not all(isinstance(v, str) for v in listed.values()):
            raise TypeError("tasks must map task ids to hashes")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ConfigError(f"dataset '{config.name}': invalid {DATASET_MANIFEST}: {exc}") from exc
    problems = [f"{t.task_id}: not listed" for t in tasks if t.task_id not in listed]
    problems += [
        f"{t.task_id}: hash differs from {DATASET_MANIFEST}"
        for t in tasks
        if t.task_id in listed and listed[t.task_id] != t.content_hash
    ]
    if config.task_names is None and config.n_tasks is None:
        loaded = {t.task_id for t in tasks}
        problems += [f"{name}: listed but missing" for name in sorted(listed) if name not in loaded]
    if problems:
        raise ConfigError(
            f"dataset '{config.name}' does not match {DATASET_MANIFEST}: " + "; ".join(problems[:10])
        )


def _finish(
    config: DatasetConfig, root: Path, boundary: Path, revision: str | None, location: str, path: str
) -> LoadedDataset:
    tasks = _select(config, root, boundary)
    _verify(config, root, tasks)
    provenance = Provenance(
        source_type=config.source.type,
        location=location,
        revision=revision,
        path=path,
        license=config.license,
        redistributable=config.redistributable,
    )
    return LoadedDataset(config, revision or tasks_hash(tasks), tasks, provenance)


class LocalDataset:
    """A directory of Harbor task directories."""

    def load(self, config: DatasetConfig) -> LoadedDataset:
        if not isinstance(config.source, LocalSource):
            raise ConfigError(f"dataset '{config.name}' is not a local source")
        return _finish(
            config, Path(config.source.path), Path(config.source.path), None, config.source.path, "."
        )


class GitDataset:
    """A git repository at a pinned commit, fetched into a cache and verified on every load.

    `remotes` maps a configured URL to the URL actually fetched; tests use it to fetch from a local
    repository without loosening the https-only config check. The cache is keyed by the configured URL.
    """

    def __init__(
        self,
        cache: Path | None = None,
        offline: bool | None = None,
        remotes: Mapping[str, str] | None = None,
    ) -> None:
        self.cache = _cache_root(cache)
        self.offline = _is_offline(offline)
        self.remotes = dict(remotes or {})

    def _git(self, cwd: Path, *args: str, remote: bool = False) -> str:
        env = {
            k: os.environ[k]
            for k in ("PATH", "https_proxy", "HTTPS_PROXY", "no_proxy", "NO_PROXY", "SSL_CERT_FILE")
            if k in os.environ
        }
        env |= {
            "HOME": str(self.cache),
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_LFS_SKIP_SMUDGE": "1",
            "GIT_ALLOW_PROTOCOL": "https:file" if self.remotes else "https",
            "LC_ALL": "C",
        }
        command = [
            "git", "-c", "core.hooksPath=/dev/null", "-c", "credential.helper=", "-c", "core.fsmonitor=false",
            "-c", "submodule.recurse=false", "-c", "filter.lfs.smudge=", "-c", "filter.lfs.process=",
            "-c", "filter.lfs.required=false", "-c", "advice.detachedHead=false", *args,
        ]  # fmt: skip
        try:
            out = subprocess.run(  # noqa: S603
                command,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=900 if remote else 120,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise ConfigError(f"git {args[0]} failed to run: {exc}") from exc
        if out.returncode != 0:
            raise ConfigError(f"git {args[0]} failed: {out.stderr.strip()[-500:]}")
        return out.stdout

    def _fetch(self, source: GitSource, target: Path) -> None:
        url = self.remotes.get(source.url, source.url)
        work = target.with_name(f"{target.name}.tmp-{os.getpid()}-{uuid.uuid4().hex[:8]}")
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True)
        try:
            self._git(work, "init", "--quiet")
            try:
                self._git(
                    work,
                    "fetch",
                    "--quiet",
                    "--depth",
                    "1",
                    "--no-tags",
                    "--no-recurse-submodules",
                    url,
                    source.commit,
                    remote=True,
                )
            except ConfigError as exc:
                raise ConfigError(f"cannot fetch commit {source.commit} from {source.url}: {exc}") from exc
            self._git(work, "checkout", "--quiet", "--detach", source.commit)
            try:
                work.rename(target)
            except OSError:
                if not (target / ".git").is_dir():  # otherwise a concurrent fetch won; verify its result
                    raise
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def _check(self, source: GitSource, repo: Path) -> None:
        head = self._git(repo, "rev-parse", "HEAD").strip()
        if head != source.commit:
            raise ConfigError(f"cached checkout {repo} is at {head}, expected {source.commit}")
        dirty = self._git(repo, "status", "--porcelain", "--untracked-files=all", "--ignored").strip()
        if dirty:
            raise ConfigError(
                f"cached checkout {repo} was modified: {dirty.splitlines()[0]}; delete it to refetch"
            )

    def load(self, config: DatasetConfig) -> LoadedDataset:
        if not isinstance(config.source, GitSource):
            raise ConfigError(f"dataset '{config.name}' is not a git source")
        _require_license(config)
        source = config.source
        repo = self.cache / "git" / hashlib.sha256(source.url.encode()).hexdigest()[:16] / source.commit
        if not (repo / ".git").is_dir():
            if self.offline:
                raise ConfigError(
                    f"dataset '{config.name}': offline and {source.url}@{source.commit} is not cached"
                )
            repo.parent.mkdir(parents=True, exist_ok=True)
            self._fetch(source, repo)
        self._check(source, repo)
        return _finish(config, repo / source.path, repo, source.commit, source.url, source.path)


class HuggingFaceDataset:
    """A Hugging Face dataset repository at a pinned commit. Files are downloaded, never executed:
    the `datasets` library (and so dataset loading scripts) is not used."""

    def __init__(self, cache: Path | None = None, offline: bool | None = None) -> None:
        self.cache = _cache_root(cache)
        self.offline = _is_offline(offline)

    def load(self, config: DatasetConfig) -> LoadedDataset:
        if not isinstance(config.source, HuggingFaceSource):
            raise ConfigError(f"dataset '{config.name}' is not a Hugging Face source")
        _require_license(config)
        source = config.source
        try:
            from huggingface_hub import snapshot_download
            from huggingface_hub.file_download import read_download_metadata  # type: ignore[attr-defined]
        except ImportError as exc:
            raise ConfigError(
                "Hugging Face datasets need the 'hf' extra: pip install 'agent-harness-lab[hf]'"
            ) from exc
        prefix = "" if source.path == "." else source.path.strip("/") + "/"
        patterns = (
            None
            if config.task_names is None
            else [f"{prefix}{DATASET_MANIFEST}", *(f"{prefix}{name}/*" for name in config.task_names)]
        )
        key = hashlib.sha256(json.dumps(patterns).encode()).hexdigest()[:12]
        local = self.cache / "huggingface" / source.repo.replace("/", "--") / source.revision / key
        try:
            snapshot_download(
                repo_id=source.repo,
                repo_type="dataset",
                revision=source.revision,
                local_dir=local,
                allow_patterns=patterns,
                token=False,
                local_files_only=self.offline,
            )
        except Exception as exc:  # hub errors are many and version dependent
            if self.offline:
                raise ConfigError(
                    f"dataset '{config.name}': offline and {source.repo}@{source.revision} is not cached"
                ) from exc
            raise ConfigError(
                f"dataset '{config.name}': cannot download {source.repo}@{source.revision}: {exc}"
            ) from exc
        root = local / source.path
        files = [
            p.relative_to(local).as_posix()
            for p in sorted(local.rglob("*"))
            if p.is_file() and ".cache" not in p.relative_to(local).parts[:1]
        ]
        if not files:
            raise ConfigError(
                f"dataset '{config.name}': {source.repo}@{source.revision} has no files for the selection"
            )
        etags = {}
        for file in files:
            meta = read_download_metadata(local, file)
            if meta is None or meta.commit_hash != source.revision:
                found = None if meta is None else meta.commit_hash
                raise ConfigError(
                    f"dataset '{config.name}': {file} comes from commit {found}, expected {source.revision}"
                )
            if not _etag_matches(local / file, meta.etag):
                raise ConfigError(f"dataset '{config.name}': {file} does not match its recorded etag")
            etags[file] = meta.etag
        marker = local / ".cache" / COMPLETE_MARKER
        if self.offline:
            try:
                complete = json.loads(marker.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ConfigError(
                    f"dataset '{config.name}': offline and the cached download of {source.repo} is incomplete"
                ) from exc
            if complete != etags:
                raise ConfigError(f"dataset '{config.name}': cached files differ from the completed download")
        else:
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps(etags, sort_keys=True), encoding="utf-8")
        return _finish(config, root, local, source.revision, source.repo, source.path)
