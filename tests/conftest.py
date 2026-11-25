from pathlib import Path
from typing import Any

import pytest

from agent_harness_lab.core.config import EvalConfig
from agent_harness_lab.core.results import Outcome, TrialResult

ROOT = Path(__file__).resolve().parents[1]


def make_task(root: Path, name: str, *, repository: str | None = None, body: str = "x") -> Path:
    task = root / name
    (task / "tests").mkdir(parents=True)
    meta = f'[metadata]\nrepository = "{repository}"\n' if repository else "[metadata]\n"
    (task / "task.toml").write_text(meta)
    (task / "instruction.md").write_text(body)
    (task / "tests" / "test.sh").write_text("exit 0\n")
    return task


@pytest.fixture
def tasks(tmp_path: Path) -> Path:
    root = tmp_path / "tasks"
    for i in range(6):
        make_task(root, f"t{i}", body=f"task {i}")
    return root


def eval_dict(tasks: Path, out: Path, **over: Any) -> dict[str, Any]:
    return {
        "kind": "eval",
        "name": "base",
        "seed": 7,
        "output_dir": str(out),
        "model": {"id": "mock/m"},
        "inference": {"backend": "mock"},
        "harnesses": [{"name": "pi", "version": "1.0.0"}, {"name": "opencode", "version": "1.0.0"}],
        "datasets": [{"name": "d", "source": {"type": "local", "path": str(tasks)}, "split": "smoke"}],
        "runner": {"type": "mock"},
        **over,
    }


@pytest.fixture
def config(tasks: Path, tmp_path: Path) -> EvalConfig:
    return EvalConfig.model_validate(eval_dict(tasks, tmp_path / "runs"))


def trial(task: str = "t0", outcome: str = "solved", **over: Any) -> TrialResult:
    o = Outcome(outcome)
    return TrialResult.model_validate(
        {
            "simulated": True,
            "dataset": "d",
            "task_id": task,
            "task_hash": "h",
            "harness": "pi",
            "harness_version": "1",
            "attempt": 1,
            "seed": 0,
            "outcome": o,
            "rewards": {"reward": 1.0} if o is Outcome.SOLVED else None,
            "error": "boom" if o is Outcome.INFRA_ERROR else None,
            **over,
        }
    )
