from pathlib import Path

import pytest
from conftest import ROOT, make_task

from agent_harness_lab.core.config import DatasetConfig
from agent_harness_lab.dataset.audit import audit
from agent_harness_lab.dataset.loaders import GitDataset, HuggingFaceDataset, LocalDataset
from agent_harness_lab.errors import ConfigError, FeatureNotImplementedError


def cfg(path: Path, split: str = "train", **over: object) -> DatasetConfig:
    return DatasetConfig.model_validate(
        {"name": path.name, "source": {"type": "local", "path": str(path)}, "split": split, **over}
    )


def test_revision_tracks_content_including_hidden_tests(tasks: Path) -> None:
    before = LocalDataset().load(cfg(tasks))
    assert before == LocalDataset().load(cfg(tasks))
    (tasks / "t0/tests/test.sh").write_text("exit 1\n")
    assert LocalDataset().load(cfg(tasks)).revision != before.revision


def test_hash_ignores_caches_but_not_the_executable_bit(tasks: Path) -> None:
    before = LocalDataset().load(cfg(tasks)).revision
    (tasks / "t0/__pycache__").mkdir()
    (tasks / "t0/__pycache__/x.pyc").write_text("x")
    assert LocalDataset().load(cfg(tasks)).revision == before
    (tasks / "t0/tests/test.sh").chmod(0o755)
    assert LocalDataset().load(cfg(tasks)).revision != before


def test_selection(tasks: Path) -> None:
    ids = [t.task_id for t in LocalDataset().load(cfg(tasks, task_names=["t[123]"], n_tasks=2)).tasks]
    assert ids == ["t1", "t2"]
    with pytest.raises(ConfigError, match="no task matches"):
        LocalDataset().load(cfg(tasks, task_names=["t1", "typo"]))


def test_invalid_tasks(tasks: Path, tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="no such directory"):
        LocalDataset().load(cfg(tmp_path / "none"))
    (tmp_path / "empty").mkdir()
    with pytest.raises(ConfigError, match="no tasks"):
        LocalDataset().load(cfg(tmp_path / "empty"))
    (tasks / "t0/link").symlink_to("/etc/hostname")
    with pytest.raises(ConfigError, match="symlink"):
        LocalDataset().load(cfg(tasks))
    make_task(tmp_path / "multi", "m")
    with (tmp_path / "multi/m/task.toml").open("a") as f:
        f.write('\n[[steps]]\nname = "one"\n')
    with pytest.raises(ConfigError, match="multi-step"):
        LocalDataset().load(cfg(tmp_path / "multi"))


def test_remote_sources_are_not_implemented() -> None:
    for loader, source in (
        (HuggingFaceDataset(), {"type": "huggingface", "repo": "a/b", "revision": "a" * 40}),
        (GitDataset(), {"type": "git", "url": "https://x", "commit": "a" * 40}),
    ):
        config = DatasetConfig.model_validate({"name": "n", "source": source, "split": "test"})
        with pytest.raises(FeatureNotImplementedError):
            loader.load(config)


def test_audit(tmp_path: Path) -> None:
    train, held = tmp_path / "train", tmp_path / "held"
    make_task(train, "same", repository="Org/Repo", body="Same  Task")
    make_task(held, "same", repository="org/repo", body="same task")
    for root in (train, held):
        make_task(root, "copy", body="identical")
    make_task(train, "canary", repository="a/b", body="terminal-bench-canary GUID 123")
    make_task(train, "unknown", body="u")
    report = audit([LocalDataset().load(cfg(train))], [LocalDataset().load(cfg(held, "test"))])
    assert report.shared_content == ["train/copy"]
    assert report.shared_instructions == ["train/copy", "train/same"]
    assert report.shared_repositories == ["org/repo"]
    assert report.canary_tasks == ["train/canary"]
    assert report.train_tasks_without_repository == 2
    assert report.leaked and not report.repository_check_complete


def test_audit_clean_and_wrong_split(tmp_path: Path) -> None:
    make_task(tmp_path / "a", "x", repository="o/a", body="1")
    make_task(tmp_path / "b", "y", repository="o/b", body="2")
    held = [LocalDataset().load(cfg(tmp_path / "b", "test"))]
    clean = audit([LocalDataset().load(cfg(tmp_path / "a"))], held)
    assert not clean.leaked and clean.repository_check_complete
    assert audit([LocalDataset().load(cfg(tmp_path / "a", "test"))], held).non_train_datasets == ["a"]


def test_smoke_tasks_load() -> None:
    loaded = LocalDataset().load(cfg(ROOT / "examples/smoke_tasks/tasks", "smoke"))
    assert 10 <= len(loaded.tasks) <= 20
    for task in loaded.tasks:
        assert (task.path / "tests/test.sh").is_file() and (task.path / "solution/solve.sh").is_file()
