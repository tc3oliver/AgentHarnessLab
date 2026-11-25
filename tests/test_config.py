from pathlib import Path

import pytest
from conftest import ROOT, eval_dict
from pydantic import ValidationError

from agent_harness_lab.core.config import (
    EvalConfig,
    GitSource,
    HardwareConfig,
    InferenceConfig,
    TrainConfig,
    load_dataset_config,
    load_experiment,
    read_yaml,
)
from agent_harness_lab.errors import ConfigError


@pytest.mark.parametrize("path", sorted((ROOT / "configs/experiments").glob("*.yaml")), ids=lambda p: p.name)
def test_shipped_experiments_are_valid(path: Path) -> None:
    load_experiment(path)


@pytest.mark.parametrize("path", sorted((ROOT / "configs/datasets").glob("*.yaml")), ids=lambda p: p.name)
def test_shipped_datasets_are_valid(path: Path) -> None:
    load_dataset_config(path)


def test_include_overrides_and_relative_paths(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub/a.yaml").write_text("x: 1\ny: 2\n")
    (tmp_path / "top.yaml").write_text("k: {include: sub/a.yaml, y: 3}\n")
    assert read_yaml(tmp_path / "top.yaml") == {"k": {"x": 1, "y": 3}}


def test_include_cycle(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text("{include: b.yaml}\n")
    (tmp_path / "b.yaml").write_text("{include: a.yaml}\n")
    with pytest.raises(ConfigError, match="cycle"):
        read_yaml(tmp_path / "a.yaml")


@pytest.mark.parametrize("text", ["a: [", "kind: nope\n", "[]\n", ""])
def test_bad_files_are_config_errors(tmp_path: Path, text: str) -> None:
    path = tmp_path / "x.yaml"
    path.write_text(text)
    with pytest.raises(ConfigError):
        load_experiment(path)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="cannot read"):
        load_experiment(tmp_path / "none.yaml")


@pytest.mark.parametrize(
    "over",
    [
        {"unknown_key": 1},
        {"name": "../escape"},
        {"harnesses": []},
        *(
            {"harnesses": [{"name": "pi", "version": v}]}
            for v in ("latest", "1.6", "^1", "main", "beta", "1.x", "")
        ),
        {"harnesses": [{"name": "pi", "version": "1.0.0", "options": {"api_key": "x"}}]},
        {"harnesses": [{"name": "pi", "version": "1.0.0"}, {"name": "pi", "version": "2.0.0"}]},
        {"model": {"id": "m", "revision": "main"}},
        {"runner": {"type": "harbor", "version": "0.25.0"}},
    ],
)
def test_rejected_eval_configs(tmp_path: Path, over: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EvalConfig.model_validate(eval_dict(tmp_path, tmp_path, **over))


def test_real_runs_need_a_pinned_model_and_no_train_split(tmp_path: Path) -> None:
    real = {
        "runner": {"type": "harbor", "version": "0.25.0"},
        "inference": {"backend": "vllm", "base_url": "http://localhost:8000/v1"},
    }
    with pytest.raises(ValidationError, match="revision"):
        EvalConfig.model_validate(eval_dict(tmp_path, tmp_path, **real))
    data = eval_dict(tmp_path, tmp_path, **real, model={"id": "m", "revision": "a" * 40})
    EvalConfig.model_validate(data)
    data["datasets"][0]["split"] = "train"
    with pytest.raises(ValidationError, match="train splits"):
        EvalConfig.model_validate(data)


@pytest.mark.parametrize(
    "over",
    [
        {"base_url": None},
        {"base_url": "http://user:pw@host/v1"},
        {"base_url": "http://host/v1?key=1"},
        {"base_url": "ftp://host"},
        {"api_key_env": "sk-not a name"},
        {"server_args": {"api-key": "x"}},
        {"server_args": {"proxy": "http://u:p@h"}},
    ],
)
def test_endpoints_cannot_carry_secrets(over: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        InferenceConfig.model_validate({"backend": "vllm", "base_url": "http://h/v1", **over})


def test_devices_are_disjoint() -> None:
    with pytest.raises(ValidationError, match="more than one role"):
        HardwareConfig.model_validate(
            {
                "allocations": [
                    {"role": "inference", "device_ids": [0]},
                    {"role": "training", "device_ids": [0]},
                ]
            }
        )


@pytest.mark.parametrize("split", ["test", "smoke", "validation"])
def test_training_refuses_non_train_splits(split: str) -> None:
    data = read_yaml(ROOT / "configs/experiments/joint_rl.yaml")
    TrainConfig.model_validate(data)
    data["train_datasets"][0]["split"] = split
    with pytest.raises(ValidationError, match="split 'train'"):
        TrainConfig.model_validate(data)


def test_git_urls_cannot_carry_credentials() -> None:
    for url in ("https://user:token@h/x.git", "ssh://h/x", "file:///etc"):
        with pytest.raises(ValidationError):
            GitSource.model_validate({"type": "git", "url": url, "commit": "a" * 40})
