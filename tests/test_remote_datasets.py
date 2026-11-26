import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from conftest import ROOT, make_task

from agent_harness_lab.core.config import DatasetConfig, load_dataset_config
from agent_harness_lab.core.manifest import new_manifest
from agent_harness_lab.dataset.audit import audit
from agent_harness_lab.dataset.loaders import (
    COMPLETE_MARKER,
    GitDataset,
    HuggingFaceDataset,
    LocalDataset,
    hash_task,
    tasks_hash,
)
from agent_harness_lab.dataset.splits import SplitFile, split_by_repository
from agent_harness_lab.errors import ConfigError

URL = "https://example.invalid/org/tasks"
GIT_ENV = ("-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false")


def blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()


def git(cwd: Path, *args: str) -> str:
    out = subprocess.run(  # noqa: S603
        ["git", *GIT_ENV, *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.strip()


@pytest.fixture
def origin(tmp_path: Path) -> tuple[Path, str]:
    repo = tmp_path / "origin"
    for i in range(4):
        make_task(repo / "tasks", f"t{i}", repository=f"org/repo{i % 2}", body=f"task {i}")
    make_task(repo / "other", "x")
    git(tmp_path, "init", "-q", str(repo))
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "tasks")
    return repo, git(repo, "rev-parse", "HEAD")


def git_cfg(commit: str, **over: Any) -> DatasetConfig:
    source = {"type": "git", "url": URL, "commit": commit, "path": "tasks"}
    return DatasetConfig.model_validate(
        {"name": "g", "source": source, "split": "train", "license": "Apache-2.0", **over}
    )


def loader(tmp_path: Path, repo: Path, offline: bool = False) -> GitDataset:
    return GitDataset(cache=tmp_path / "cache", offline=offline, remotes={URL: str(repo)})


def cached(tmp_path: Path) -> Path:
    return next((tmp_path / "cache/git").glob("*/*"))


def test_git_pinned_load_is_stable(tmp_path: Path, origin: tuple[Path, str]) -> None:
    repo, commit = origin
    first = loader(tmp_path, repo).load(git_cfg(commit))
    assert [t.task_id for t in first.tasks] == ["t0", "t1", "t2", "t3"]
    assert first.revision == commit and first.provenance is not None
    assert (first.provenance.source_type, first.provenance.location, first.provenance.path) == (
        "git",
        URL,
        "tasks",
    )
    (repo / "tasks/t0/instruction.md").write_text("moved on")  # upstream changes do not matter
    git(repo, "commit", "-qam", "later")
    again = loader(tmp_path, repo, offline=True).load(git_cfg(commit))
    assert again == first
    assert tasks_hash(again.tasks) == tasks_hash(first.tasks)


def test_git_wrong_commit_fails(tmp_path: Path, origin: tuple[Path, str]) -> None:
    with pytest.raises(ConfigError, match="cannot fetch commit"):
        loader(tmp_path, origin[0]).load(git_cfg("b" * 40))
    assert not list((tmp_path / "cache").glob("git/*/*"))


def test_git_missing_path_fails(tmp_path: Path, origin: tuple[Path, str]) -> None:
    config = git_cfg(origin[1])
    config = config.model_copy(update={"source": config.source.model_copy(update={"path": "nope"})})
    with pytest.raises(ConfigError, match="no such directory"):
        loader(tmp_path, origin[0]).load(config)


@pytest.mark.parametrize("tamper", ["modify", "untracked", "wrong_head"])
def test_git_tampered_cache_fails(tmp_path: Path, origin: tuple[Path, str], tamper: str) -> None:
    repo, commit = origin
    loader(tmp_path, repo).load(git_cfg(commit))
    root = cached(tmp_path)
    if tamper == "modify":
        (root / "tasks/t1/tests/test.sh").write_text("exit 0  # edited\n")
    elif tamper == "untracked":
        (root / "tasks/t1/extra.txt").write_text("x")
    else:
        git(root, "commit", "-q", "--allow-empty", "-m", "other")
    with pytest.raises(ConfigError, match=r"modified|expected"):
        loader(tmp_path, repo, offline=True).load(git_cfg(commit))


def test_git_offline(tmp_path: Path, origin: tuple[Path, str], monkeypatch: pytest.MonkeyPatch) -> None:
    repo, commit = origin
    with pytest.raises(ConfigError, match="offline"):
        loader(tmp_path, repo, offline=True).load(git_cfg(commit))
    monkeypatch.setenv("AGENTLAB_OFFLINE", "1")
    monkeypatch.setenv("AGENTLAB_CACHE", str(tmp_path / "cache"))
    with pytest.raises(ConfigError, match="offline"):
        GitDataset(remotes={URL: str(repo)}).load(git_cfg(commit))
    monkeypatch.delenv("AGENTLAB_OFFLINE")
    GitDataset(remotes={URL: str(repo)}).load(git_cfg(commit))  # cache root from the environment
    monkeypatch.setenv("AGENTLAB_OFFLINE", "1")
    GitDataset(remotes={URL: str(repo)}).load(git_cfg(commit))


def test_unknown_licence_is_refused(tmp_path: Path, origin: tuple[Path, str]) -> None:
    with pytest.raises(ConfigError, match=r"unknown licence.*DATASETS\.md"):
        loader(tmp_path, origin[0]).load(git_cfg(origin[1], license=None))
    assert not (tmp_path / "cache").exists()
    hf = DatasetConfig.model_validate(
        {"name": "h", "source": {"type": "huggingface", "repo": "a/b", "revision": "a" * 40}, "split": "test"}
    )
    with pytest.raises(ConfigError, match="unknown licence"):
        HuggingFaceDataset(cache=tmp_path / "c").load(hf)


def test_tasks_hash_pin(tmp_path: Path, origin: tuple[Path, str]) -> None:
    repo, commit = origin
    good = tasks_hash(loader(tmp_path, repo).load(git_cfg(commit)).tasks)
    assert loader(tmp_path, repo).load(git_cfg(commit, tasks_hash=good)).tasks
    with pytest.raises(ConfigError, match="task-list hash"):
        loader(tmp_path, repo).load(git_cfg(commit, tasks_hash="sha256:" + "0" * 64))
    with pytest.raises(ValueError, match="String should match"):
        git_cfg(commit, tasks_hash="abc")


def write_manifest(root: Path, **over: str) -> None:
    listed = {p.name: hash_task(p) for p in sorted(root.iterdir()) if (p / "task.toml").is_file()}
    (root / "dataset-manifest.json").write_text(json.dumps({"tasks": {**listed, **over}}))


def test_dataset_manifest_local(tasks: Path, tmp_path: Path) -> None:
    config = DatasetConfig.model_validate(
        {"name": "l", "source": {"type": "local", "path": str(tasks)}, "split": "smoke"}
    )
    write_manifest(tasks)
    assert len(LocalDataset().load(config).tasks) == 6
    (tasks / "t0/instruction.md").write_text("changed")
    with pytest.raises(ConfigError, match="t0: hash differs"):
        LocalDataset().load(config)
    write_manifest(tasks)
    make_task(tasks, "unlisted")
    with pytest.raises(ConfigError, match="unlisted: not listed"):
        LocalDataset().load(config)
    shutil.rmtree(tasks / "unlisted")
    write_manifest(tasks, ghost="0" * 64)
    with pytest.raises(ConfigError, match="ghost: listed but missing"):
        LocalDataset().load(config)
    selected = config.model_copy(update={"task_names": ["t1"]})
    assert [t.task_id for t in LocalDataset().load(selected).tasks] == ["t1"]
    (tasks / "dataset-manifest.json").write_text("[]")
    with pytest.raises(ConfigError, match="invalid dataset-manifest"):
        LocalDataset().load(config)


def test_dataset_manifest_git(tmp_path: Path, origin: tuple[Path, str]) -> None:
    repo, _ = origin
    write_manifest(repo / "tasks", t2="f" * 64)
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "manifest")
    with pytest.raises(ConfigError, match="t2: hash differs"):
        loader(tmp_path, repo).load(git_cfg(git(repo, "rev-parse", "HEAD")))


def test_version_and_provenance_in_manifest(tmp_path: Path, origin: tuple[Path, str], config: Any) -> None:
    repo, commit = origin
    loaded = loader(tmp_path, repo).load(git_cfg(commit, version="3", redistributable=True))
    info = new_manifest(config, [loaded], 1, True, {}).datasets[0]
    assert (info.version, info.source_type, info.source, info.source_revision, info.source_path) == (
        "3",
        "git",
        URL,
        commit,
        "tasks",
    )
    assert info.tasks_hash == tasks_hash(loaded.tasks) and info.tasks_hash.startswith("sha256:")
    assert info.redistributable is True and info.license == "Apache-2.0"
    old = info.model_dump(
        exclude={"version", "source_type", "source", "source_revision", "source_path", "redistributable"}
    )
    assert type(info).model_validate(old).source is None  # manifests written before these fields still load


def test_smoke_version_changes_comparability(config: Any) -> None:
    smoke = load_dataset_config(ROOT / "configs/datasets/smoke.yaml")
    assert smoke.version == "2"
    loaded = LocalDataset().load(smoke)
    v1 = loaded.__class__(
        smoke.model_copy(update={"version": None}), loaded.revision, loaded.tasks, loaded.provenance
    )
    a = new_manifest(config, [loaded], 1, True, {}).comparability()
    b = new_manifest(config, [v1], 1, True, {}).comparability()
    assert a != b


def test_smoke_duration_instruction_states_integers() -> None:
    text = (ROOT / "examples/smoke_tasks/tasks/ahl-fix-duration-parse/instruction.md").read_text()
    assert "non-negative integer" in text and "1.5h" in text


def test_audit_works_on_git_datasets(tmp_path: Path, origin: tuple[Path, str]) -> None:
    repo, commit = origin
    train = loader(tmp_path, repo).load(git_cfg(commit))
    held = make_task(tmp_path / "held", "h", repository="org/repo0", body="other")
    assert held.exists()
    held_cfg = DatasetConfig.model_validate(
        {"name": "held", "source": {"type": "local", "path": str(tmp_path / "held")}, "split": "test"}
    )
    report = audit([train], [LocalDataset().load(held_cfg)])
    assert report.shared_repositories == ["org/repo0"] and report.leaked


def test_audit_cli_on_git_dataset(
    tmp_path: Path, origin: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Goes through the registry: registry-built loader; cache from the environment."""
    repo, commit = origin
    monkeypatch.setenv("AGENTLAB_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(GitDataset, "__init__", _init_with_remote(repo))
    from typer.testing import CliRunner

    from agent_harness_lab.cli import app

    yaml = tmp_path / "train.yaml"
    source = f"{{type: git, url: {URL}, commit: {commit}, path: tasks}}"
    yaml.write_text(f"name: g\nsplit: train\nlicense: Apache-2.0\nsource: {source}\n")
    out = CliRunner().invoke(app, ["audit", "--train", str(yaml), "--eval", "configs/datasets/smoke.yaml"])
    assert out.exit_code == 0, out.output
    assert '"shared_content": []' in out.output


def _init_with_remote(repo: Path) -> Any:
    original = GitDataset.__init__

    def init(
        self: GitDataset, cache: Path | None = None, offline: bool | None = None, remotes: Any = None
    ) -> None:
        original(self, cache, offline, {URL: str(repo)})

    return init


# Hugging Face, with a fake snapshot_download that mimics huggingface_hub's local_dir download.


@pytest.fixture
def hub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    pytest.importorskip("huggingface_hub")
    import huggingface_hub
    from huggingface_hub._local_folder import write_download_metadata

    remote = tmp_path / "hub"
    for i in range(3):
        make_task(remote / "tasks", f"t{i}", repository=f"org/r{i}", body=f"hf {i}")
    state: dict[str, Any] = {"remote": remote, "calls": [], "commit": "c" * 40}

    def fake(**kw: Any) -> str:
        from fnmatch import fnmatch

        state["calls"].append(kw)
        local = Path(kw["local_dir"])
        if kw["local_files_only"]:
            if not local.is_dir():
                raise FileNotFoundError("not cached")
            return str(local)
        for file in sorted(p for p in remote.rglob("*") if p.is_file()):
            name = file.relative_to(remote).as_posix()
            if kw["allow_patterns"] is None or any(fnmatch(name, pat) for pat in kw["allow_patterns"]):
                (local / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(file, local / name)
                write_download_metadata(local, name, state["commit"], blob_sha1(file.read_bytes()))
        return str(local)

    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake)
    return state


def hf_cfg(**over: Any) -> DatasetConfig:
    source = {"type": "huggingface", "repo": "org/ds", "revision": "c" * 40, "path": "tasks"}
    return DatasetConfig.model_validate(
        {"name": "h", "source": source, "split": "train", "license": "MIT", **over}
    )


def test_hf_load_offline_and_arguments(tmp_path: Path, hub: dict[str, Any]) -> None:
    loader_ = HuggingFaceDataset(cache=tmp_path / "cache")
    first = loader_.load(hf_cfg())
    assert [t.task_id for t in first.tasks] == ["t0", "t1", "t2"] and first.revision == "c" * 40
    call = hub["calls"][0]
    assert call["repo_type"] == "dataset" and call["revision"] == "c" * 40 and call["token"] is False
    assert call["allow_patterns"] is None
    offline = HuggingFaceDataset(cache=tmp_path / "cache", offline=True).load(hf_cfg())
    assert offline == first and hub["calls"][1]["local_files_only"] is True
    with pytest.raises(ConfigError, match="offline"):
        HuggingFaceDataset(cache=tmp_path / "empty", offline=True).load(hf_cfg())


def test_hf_task_names_restrict_download(tmp_path: Path, hub: dict[str, Any]) -> None:
    loaded = HuggingFaceDataset(cache=tmp_path / "cache").load(hf_cfg(task_names=["t1"]))
    assert [t.task_id for t in loaded.tasks] == ["t1"]
    assert hub["calls"][0]["allow_patterns"] == ["tasks/dataset-manifest.json", "tasks/t1/*"]
    # a different selection never reuses the partial download
    assert (
        len(
            HuggingFaceDataset(cache=tmp_path / "cache", offline=True)
            .__class__(cache=tmp_path / "cache")
            .load(hf_cfg())
            .tasks
        )
        == 3
    )


def test_hf_wrong_snapshot_commit_fails(tmp_path: Path, hub: dict[str, Any]) -> None:
    hub["commit"] = "d" * 40
    with pytest.raises(ConfigError, match="expected " + "c" * 40):
        HuggingFaceDataset(cache=tmp_path / "cache").load(hf_cfg())


def test_hf_download_error_and_tasks_hash(tmp_path: Path, hub: dict[str, Any]) -> None:
    good = tasks_hash(HuggingFaceDataset(cache=tmp_path / "cache").load(hf_cfg()).tasks)
    with pytest.raises(ConfigError, match="task-list hash"):
        HuggingFaceDataset(cache=tmp_path / "cache").load(hf_cfg(tasks_hash="sha256:" + "1" * 64))
    assert HuggingFaceDataset(cache=tmp_path / "cache").load(hf_cfg(tasks_hash=good))


def test_hf_missing_extra(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(__import__("sys").modules, "huggingface_hub", None)
    with pytest.raises(ConfigError, match=r"\[hf\]"):
        HuggingFaceDataset(cache=tmp_path / "c").load(hf_cfg())


def test_source_paths_must_stay_inside() -> None:
    for bad in ("/etc", "../x", "a/../b"):
        with pytest.raises(ValueError, match="relative path"):
            DatasetConfig.model_validate(
                {
                    "name": "n",
                    "split": "test",
                    "source": {"type": "git", "url": URL, "commit": "a" * 40, "path": bad},
                }
            )


# Splits


def repo_dataset(tmp_path: Path, repos: int = 8, per: int = 3) -> Any:
    for r in range(repos):
        for i in range(per):
            make_task(tmp_path / "d", f"r{r}-{i}", repository=f"Org/Repo{r}", body=f"{r} {i}")
    config = DatasetConfig.model_validate(
        {"name": "d", "source": {"type": "local", "path": str(tmp_path / "d")}, "split": "train"}
    )
    return LocalDataset().load(config)


def test_split_is_deterministic_and_groups_repositories(tmp_path: Path) -> None:
    dataset = repo_dataset(tmp_path)
    a = split_by_repository(dataset, 0.4, 1)
    assert a == split_by_repository(dataset, 0.4, 1)
    assert a.hash != split_by_repository(dataset, 0.4, 2).hash
    repo_of = {t.task_id: t.repository for t in dataset.tasks}
    train = {repo_of[i] for i in a.train.task_ids}
    validation = {repo_of[i] for i in a.validation.task_ids}
    assert not train & validation
    assert train == set(a.train.repositories) and validation == set(a.validation.repositories)
    assert len(a.train.task_ids) + len(a.validation.task_ids) == len(dataset.tasks)
    assert a.revision == dataset.revision and a.hash.startswith("sha256:")


def test_split_errors_and_tamper(tmp_path: Path) -> None:
    dataset = repo_dataset(tmp_path)
    with pytest.raises(ConfigError, match="between 0 and 1"):
        split_by_repository(dataset, 1.0, 0)
    make_task(tmp_path / "d", "norepo")
    with pytest.raises(ConfigError, match=r"1 of 25 tasks declare no repository.*norepo"):
        split_by_repository(LocalDataset().load(dataset.config), 0.4, 0)
    split = split_by_repository(dataset, 0.4, 1)
    file = tmp_path / "split.json"
    split.write(file)
    assert SplitFile.read(file) == split
    file.write_text(file.read_text().replace('"seed": 1', '"seed": 2'))
    with pytest.raises(ConfigError, match="hash does not match"):
        SplitFile.read(file)


def test_split_cli(tmp_path: Path) -> None:
    from typer.testing import CliRunner

    from agent_harness_lab.cli import app

    repo_dataset(tmp_path)
    yaml = tmp_path / "d.yaml"
    yaml.write_text(f"name: d\nsplit: train\nsource: {{type: local, path: {tmp_path / 'd'}}}\n")
    out = tmp_path / "split.json"
    result = CliRunner().invoke(
        app, ["split", str(yaml), "--validation-fraction", "0.4", "--seed", "1", "-o", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert SplitFile.read(out).validation_fraction == 0.4


# Real downloads: pytest -m network


@pytest.mark.network
def test_real_git_download(tmp_path: Path) -> None:
    config = DatasetConfig.model_validate(
        {
            "name": "ahl-smoke",
            "split": "smoke",
            "license": "Apache-2.0",
            "source": {
                "type": "git",
                "url": "https://github.com/tc3oliver/AgentHarnessLab",
                "commit": "d7dddbec107c8b8cd9ff95a715ab8e3d67a61951",
                "path": "examples/smoke_tasks/tasks",
            },
        }
    )
    first = GitDataset(cache=tmp_path).load(config)
    assert len(first.tasks) == 12
    assert GitDataset(cache=tmp_path, offline=True).load(config).tasks == first.tasks


@pytest.mark.network
def test_real_huggingface_download(tmp_path: Path) -> None:
    pytest.importorskip("huggingface_hub")
    config = DatasetConfig.model_validate(
        {
            "name": "tb21-one",
            "split": "test",
            "license": "Apache-2.0",
            "task_names": ["adaptive-rejection-sampler"],
            "source": {
                "type": "huggingface",
                "repo": "harborframework/terminal-bench-2.1",
                "revision": "3e235dff6880252a587fa479c09bcb1e16edf2eb",
                "path": "tasks",
            },
        }
    )
    first = HuggingFaceDataset(cache=tmp_path).load(config)
    assert [t.task_id for t in first.tasks] == ["adaptive-rejection-sampler"]
    assert HuggingFaceDataset(cache=tmp_path, offline=True).load(config).tasks == first.tasks


# Review fixes


def test_git_symlinked_task_dir_or_path_is_rejected(tmp_path: Path, origin: tuple[Path, str]) -> None:
    repo, _ = origin
    outside = tmp_path / "outside"
    make_task(outside, "evil")
    (repo / "tasks/link").symlink_to(outside / "evil")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "link")
    commit = git(repo, "rev-parse", "HEAD")
    with pytest.raises(ConfigError, match="symlink"):
        loader(tmp_path, repo).load(git_cfg(commit))
    (repo / "esc").symlink_to(outside)
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "path link")
    config = git_cfg(git(repo, "rev-parse", "HEAD"))
    config = config.model_copy(update={"source": config.source.model_copy(update={"path": "esc"})})
    with pytest.raises(ConfigError, match="symlink"):
        loader(tmp_path, repo).load(config)


def test_local_symlinked_task_dir_is_rejected(tasks: Path, tmp_path: Path) -> None:
    make_task(tmp_path / "outside", "evil")
    (tasks / "link").symlink_to(tmp_path / "outside/evil")
    config = DatasetConfig.model_validate(
        {"name": "l", "source": {"type": "local", "path": str(tasks)}, "split": "smoke"}
    )
    with pytest.raises(ConfigError, match=r"symlink|outside"):
        LocalDataset().load(config)


def test_hf_content_tamper_fails(tmp_path: Path, hub: dict[str, Any]) -> None:
    HuggingFaceDataset(cache=tmp_path / "cache").load(hf_cfg())
    file = next((tmp_path / "cache/huggingface").rglob("t1/instruction.md"))
    stat = file.stat()
    file.write_text("hf X")  # same size, restored mtime: only the content check can notice
    os.utime(file, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(ConfigError, match="etag"):
        HuggingFaceDataset(cache=tmp_path / "cache", offline=True).load(hf_cfg())


def test_hf_partial_download_fails_offline(tmp_path: Path, hub: dict[str, Any]) -> None:
    cache = tmp_path / "cache"
    HuggingFaceDataset(cache=cache).load(hf_cfg())
    local = next((cache / "huggingface").glob("*/*/*"))
    (local / "tasks/t2/tests/test.sh").unlink()
    with pytest.raises(ConfigError, match="differ from the completed download"):
        HuggingFaceDataset(cache=cache, offline=True).load(hf_cfg())
    (local / ".cache" / COMPLETE_MARKER).unlink()
    with pytest.raises(ConfigError, match="incomplete"):
        HuggingFaceDataset(cache=cache, offline=True).load(hf_cfg())


def test_hf_download_without_marker_is_not_trusted_offline(tmp_path: Path, hub: dict[str, Any]) -> None:
    cache = tmp_path / "cache"
    local = cache / "huggingface/org--ds" / ("c" * 40)
    local.mkdir(parents=True)
    key = hashlib.sha256(json.dumps(None).encode()).hexdigest()[:12]
    shutil.copytree(hub["remote"], local / key)  # files with no download metadata at all
    with pytest.raises(ConfigError, match="comes from commit None"):
        HuggingFaceDataset(cache=cache, offline=True).load(hf_cfg())


def test_hf_manifest_is_downloaded_with_task_names(tmp_path: Path, hub: dict[str, Any]) -> None:
    write_manifest(hub["remote"] / "tasks", t1="0" * 64)
    with pytest.raises(ConfigError, match="t1: hash differs"):
        HuggingFaceDataset(cache=tmp_path / "cache").load(hf_cfg(task_names=["t1"]))
    assert "tasks/dataset-manifest.json" in hub["calls"][0]["allow_patterns"]


def test_split_file_hash_is_required(tmp_path: Path) -> None:
    split = split_by_repository(repo_dataset(tmp_path), 0.4, 1)
    file = tmp_path / "split.json"
    split.write(file)
    data = json.loads(file.read_text())
    for mutate in (lambda d: d.pop("hash"), lambda d: d.update(hash="")):
        broken = json.loads(json.dumps(data))
        mutate(broken)
        file.write_text(json.dumps(broken))
        with pytest.raises(ConfigError, match="invalid split file"):
            SplitFile.read(file)


def test_git_concurrent_fetch_winner_is_accepted(tmp_path: Path, origin: tuple[Path, str]) -> None:
    repo, commit = origin

    class Racing(GitDataset):
        def _git(self, cwd: Path, *args: str, remote: bool = False) -> str:
            out = super()._git(cwd, *args, remote=remote)
            if args[0] == "checkout":  # another process finishes first
                shutil.copytree(cwd, cwd.with_name(commit), symlinks=True)
            return out

    racing = Racing(cache=tmp_path / "cache", remotes={URL: str(repo)})
    assert len(racing.load(git_cfg(commit)).tasks) == 4
