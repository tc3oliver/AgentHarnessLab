import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ROOT


def agentlab(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "agent_harness_lab", *args],
        cwd=cwd,
        env={**os.environ, "NO_COLOR": "1", "COLUMNS": "200"},
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def demo(tmp_path: Path) -> Path:
    (tmp_path / "configs").symlink_to(ROOT / "configs")
    (tmp_path / "examples").symlink_to(ROOT / "examples")
    return tmp_path


def test_quick_start(demo: Path) -> None:
    for name in ("base", "joint"):
        run = agentlab("eval", "-c", f"configs/experiments/mock_{name}.yaml", cwd=demo)
        assert run.returncode == 0, run.stderr
        assert "SIMULATED RESULTS" in run.stdout
    out = agentlab("compare", "runs/base", "runs/joint", "-o", "cmp.md", cwd=demo)
    assert out.returncode == 0, out.stderr
    assert "SIMULATED RESULTS" in out.stdout and "in-harness" in out.stdout
    assert (demo / "cmp.md").read_text().strip() == out.stdout.strip()
    again = agentlab("eval", "-c", "configs/experiments/mock_base.yaml", cwd=demo)
    assert again.returncode == 4 and "Traceback" not in again.stderr


@pytest.mark.parametrize(
    ("args", "code", "message"),
    [
        (
            ("train", "-c", "configs/experiments/joint_rl.yaml"),
            3,
            "joint multi-harness RL is not implemented",
        ),
        (
            ("eval", "-c", "configs/experiments/baseline.yaml"),
            3,
            "Harbor evaluation runner is not implemented",
        ),
        (("eval", "-c", "configs/experiments/joint_rl.yaml"), 2, "training config"),
        (("train", "-c", "configs/experiments/mock_base.yaml"), 2, "evaluation config"),
        (("eval", "-c", "missing.yaml"), 2, "cannot read"),
        (("compare", "missing-a", "missing-b"), 4, "not a run directory"),
        (
            (
                "audit",
                "--train",
                "configs/datasets/smoke.yaml",
                "--eval",
                "configs/datasets/smoke.yaml",
            ),
            6,
            "leakage found",
        ),
    ],
)
def test_expected_failures(demo: Path, args: tuple[str, ...], code: int, message: str) -> None:
    out = agentlab(*args, cwd=demo)
    assert out.returncode == code, out.stderr
    assert message in out.stderr and "Traceback" not in out.stderr
    assert not (demo / "runs").exists()


def test_validate_and_version(demo: Path) -> None:
    assert agentlab("validate", "-c", "configs/experiments/baseline.yaml", cwd=demo).returncode == 0
    assert agentlab("--version").stdout.strip()
