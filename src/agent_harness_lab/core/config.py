"""Experiment configuration. Unknown keys are errors so that a typo cannot silently change an experiment.

`{include: other.yaml}` is replaced by that file's contents, relative to the including file. Keys next to
`include` override the included ones. Dataset `path` values are relative to the working directory.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

from agent_harness_lab.errors import ConfigError

CONTROL_HARNESSES = frozenset({"oracle", "nop"})
_COMMIT = re.compile(r"[0-9a-f]{40}")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _require_commit(value: str) -> str:
    if not _COMMIT.fullmatch(value):
        raise ValueError("must be a full 40-character commit hash, not a branch or tag")
    return value


def _clean_url(value: str, schemes: set[str]) -> str:
    url = urlsplit(value)
    if url.scheme not in schemes or not url.hostname:
        raise ValueError(f"must be a URL with scheme {' or '.join(sorted(schemes))}")
    if url.username or url.password or url.query:
        raise ValueError("URLs must not carry credentials or a query string")
    return value


def _reject_secrets(values: dict[str, str | int | float | bool]) -> dict[str, str | int | float | bool]:
    """Best effort: these values are copied into manifests. Names are checked, and URLs inside values."""
    for key, value in values.items():
        if re.search(r"key|token$|secret|password|credential|authorization", key, re.IGNORECASE):
            raise ValueError(f"'{key}' looks like a secret")
        if isinstance(value, str) and re.search(r"://[^/\s]*@", value):
            raise ValueError(f"'{key}' contains a URL with credentials")
    return values


class AdapterConfig(Strict):
    id: str
    revision: str

    _revision = field_validator("revision")(_require_commit)


class ModelConfig(Strict):
    id: str
    revision: str | None = None
    adapter: AdapterConfig | None = None

    @field_validator("revision")
    @classmethod
    def _revision(cls, value: str | None) -> str | None:
        return None if value is None else _require_commit(value)


class SamplingConfig(Strict):
    temperature: float = Field(0.8, ge=0)
    top_p: float = Field(1.0, gt=0, le=1)
    top_k: int | None = Field(None, ge=0)
    """Null: not declared. vLLM takes it from the model's generation_config unless overridden."""
    max_output_tokens: int | None = Field(None, gt=0)
    enable_thinking: bool = False


class InferenceConfig(Strict):
    """An OpenAI-compatible endpoint. Secrets are referenced by environment variable name, never stored."""

    backend: Literal["none", "mock", "openai_compatible", "vllm"]
    """`none` is only for the oracle and nop control agents, which call no model."""
    base_url: str | None = None
    agent_base_url: str | None = None
    """The endpoint as seen from inside a sandbox, where localhost is the sandbox. Defaults to base_url."""
    served_model: str | None = None
    """Name the server uses for the model or adapter. Defaults to model.id."""
    api_key_env: str | None = Field(None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    sampling: SamplingConfig = SamplingConfig()
    """Declared, not enforced: harnesses choose their own request parameters, so the server must apply these
    (vLLM: --override-generation-config and --default-chat-template-kwargs)."""
    server_args: dict[str, str | int | float | bool] = Field(default_factory=dict)
    """Serving flags to record for reproducibility. This project does not start servers."""

    @model_validator(mode="after")
    def _check(self) -> InferenceConfig:
        if self.backend not in {"none", "mock"} and self.base_url is None:
            raise ValueError(f"base_url is required for backend '{self.backend}'")
        for url in (self.base_url, self.agent_base_url):
            if url is not None:
                _clean_url(url, {"http", "https"})
        _reject_secrets(self.server_args)
        return self


class LocalSource(Strict):
    type: Literal["local"]
    path: str


class HuggingFaceSource(Strict):
    type: Literal["huggingface"]
    repo: str
    revision: str
    config_name: str | None = None

    _revision = field_validator("revision")(_require_commit)


class GitSource(Strict):
    type: Literal["git"]
    url: str
    commit: str
    path: str = "."

    @field_validator("url")
    @classmethod
    def _url(cls, value: str) -> str:
        return _clean_url(value, {"https"})

    _commit = field_validator("commit")(_require_commit)


type DatasetSource = Annotated[LocalSource | HuggingFaceSource | GitSource, Field(discriminator="type")]


class DatasetConfig(Strict):
    name: str
    source: DatasetSource
    split: Literal["train", "validation", "test", "smoke"]
    license: str | None = None
    """SPDX id, or null when the publisher declares none."""
    redistributable: bool = False
    notes: str = ""
    task_names: list[str] | None = None
    n_tasks: int | None = Field(None, gt=0)


class HarnessConfig(Strict):
    name: str
    version: str
    max_turns: int | None = Field(None, gt=0)
    timeout_s: float | None = Field(None, gt=0)
    setup_timeout_s: float | None = Field(None, gt=0)
    """Installing a harness into each sandbox can exceed Harbor's default of 360 s."""
    options: dict[str, str | int | float | bool] = Field(default_factory=dict)

    _options = field_validator("options")(_reject_secrets)

    @field_validator("version")
    @classmethod
    def _version(cls, value: str) -> str:
        if not re.fullmatch(r"\d+\.\d+\.\d+([-+][0-9A-Za-z.+-]+)?", value):
            raise ValueError("pin an exact harness version (x.y.z), not a tag or range")
        return value


class GpuAllocation(Strict):
    role: Literal["inference", "training"]
    device_ids: list[int] = Field(min_length=1)

    @field_validator("device_ids")
    @classmethod
    def _unique(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value) or min(value) < 0:
            raise ValueError("device_ids must be unique and non-negative")
        return value


class HardwareConfig(Strict):
    """Recorded and validated only. Nothing in this project selects or starts devices yet."""

    vendor: Literal["none", "amd", "nvidia"] = "none"
    device: str | None = None
    allocations: list[GpuAllocation] = Field(default_factory=list)

    @model_validator(mode="after")
    def _disjoint(self) -> HardwareConfig:
        ids = [i for a in self.allocations for i in a.device_ids]
        if len(ids) != len(set(ids)):
            raise ValueError("a device is assigned to more than one role")
        return self


class MockRunnerConfig(Strict):
    type: Literal["mock"]
    solve_rate: float = Field(0.5, ge=0, le=1)
    solve_rate_by_harness: dict[str, float] = Field(default_factory=dict)
    infra_error_rate: float = Field(0.0, ge=0, le=1)
    effort: float = Field(1.0, gt=0)
    """Scales simulated tool calls, tokens and latency."""


class HarborRunnerConfig(Strict):
    type: Literal["harbor"]
    version: str
    """Exact Harbor version. Checked against `command --version` before anything runs."""
    command: list[str] = Field(default=["harbor"], min_length=1)
    """Harbor runs as a subprocess, so it may live in its own environment.
    A wrapper must exec Harbor or forward SIGTERM to it, or an interrupted run leaves Harbor behind."""
    environment: str = "docker"
    n_concurrent: int = Field(1, gt=0)
    prebuilt: bool = False
    """Use images from `agentlab images` instead of installing the harness in every trial."""
    reward_key: str = "reward"
    pass_threshold: float = Field(1.0, gt=0)


type RunnerConfig = Annotated[MockRunnerConfig | HarborRunnerConfig, Field(discriminator="type")]


class CostConfig(Strict):
    """Prices used when the harness reports no cost. Leave unset to keep cost unknown."""

    usd_per_million_input: float = Field(ge=0)
    usd_per_million_output: float = Field(ge=0)


class ReportConfig(Strict):
    formats: list[Literal["jsonl", "parquet", "markdown"]] = ["jsonl", "markdown"]


class _Experiment(Strict):
    schema_version: Literal[1] = 1
    name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    output_dir: str = "runs"
    seed: int = Field(ge=0)
    model: ModelConfig
    harnesses: list[HarnessConfig] = Field(min_length=1)
    hardware: HardwareConfig = HardwareConfig()

    @model_validator(mode="after")
    def _unique_harnesses(self) -> _Experiment:
        names = [h.name for h in self.harnesses]
        if len(set(names)) != len(names):
            raise ValueError("harness names must be unique")
        return self


class EvalConfig(_Experiment):
    kind: Literal["eval"]
    inference: InferenceConfig
    datasets: list[DatasetConfig] = Field(min_length=1)
    runner: RunnerConfig
    n_attempts: int = Field(1, gt=0)
    trained_on: list[str] = Field(default_factory=list)
    """Harnesses the evaluated policy was trained in; empty for a base model. Used for transfer gain."""
    cost: CostConfig | None = None
    report: ReportConfig = ReportConfig()

    @model_validator(mode="after")
    def _check(self) -> EvalConfig:
        names = [d.name for d in self.datasets]
        if len(set(names)) != len(names):
            raise ValueError("dataset names must be unique")
        if (self.runner.type == "mock") != (self.inference.backend == "mock"):
            raise ValueError("runner 'mock' and inference backend 'mock' must be used together")
        controls = [h.name for h in self.harnesses if h.name in CONTROL_HARNESSES]
        if self.runner.type != "mock":
            if (self.inference.backend == "none") != (len(controls) == len(self.harnesses)):
                raise ValueError("inference backend 'none' is for runs where every harness is oracle or nop")
            if controls and len(controls) != len(self.harnesses):
                raise ValueError("do not mix oracle or nop with model-driven harnesses in one run")
            if self.inference.backend != "none" and self.model.revision is None:
                raise ValueError("model.revision is required for model-driven runs")
            train = [d.name for d in self.datasets if d.split == "train"]
            if train:
                raise ValueError(f"evaluation must not use train splits: {train}")
        return self


class LoraConfig(Strict):
    r: int = Field(gt=0)
    alpha: int = Field(gt=0)
    target_modules: list[str] | Literal["all-linear"]


class TrainerConfig(Strict):
    backend: Literal["trl"] = "trl"
    algorithm: Literal["async_grpo"] = "async_grpo"
    group_by: Literal["task_harness"] = "task_harness"
    learning_rate: float = Field(gt=0)
    max_steps: int = Field(gt=0)
    num_generations: int = Field(gt=1)
    temperature: float = Field(0.8, gt=0)
    max_staleness: int = Field(4, ge=0)
    tool_efficiency_weight: float = Field(0.0, ge=0)
    lora: LoraConfig


class TrainConfig(_Experiment):
    kind: Literal["train"]
    train_datasets: list[DatasetConfig] = Field(min_length=1)
    validation_datasets: list[DatasetConfig] = Field(default_factory=list)
    trainer: TrainerConfig

    @model_validator(mode="after")
    def _splits(self) -> TrainConfig:
        bad = [d.name for d in self.train_datasets if d.split != "train"]
        if bad:
            raise ValueError(f"train_datasets may only use split 'train': {bad}")
        bad = [d.name for d in self.validation_datasets if d.split != "validation"]
        if bad:
            raise ValueError(f"validation_datasets may only use split 'validation': {bad}")
        if self.model.revision is None:
            raise ValueError("model.revision is required for training")
        return self


type ExperimentConfig = Annotated[EvalConfig | TrainConfig, Field(discriminator="kind")]
_EXPERIMENT: TypeAdapter[EvalConfig | TrainConfig] = TypeAdapter(ExperimentConfig)


def read_yaml(path: Path, _stack: tuple[Path, ...] = ()) -> Any:
    path = path.resolve()
    if path in _stack:
        raise ConfigError(f"include cycle at {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc.strerror}") from exc
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    return _expand(data, path, (*_stack, path))


def _expand(node: Any, path: Path, stack: tuple[Path, ...]) -> Any:
    if isinstance(node, list):
        return [_expand(item, path, stack) for item in node]
    if not isinstance(node, dict):
        return node
    values = {k: _expand(v, path, stack) for k, v in node.items() if k != "include"}
    if "include" not in node:
        return values
    target = node["include"]
    if not isinstance(target, str):
        raise ConfigError(f"include must be a file path in {path}")
    base = read_yaml(path.parent / target, stack)
    if not isinstance(base, dict):
        raise ConfigError(f"included file {target} must contain a mapping")
    return {**base, **values}


def _format(exc: ValidationError) -> str:
    return "\n".join(f"  {'.'.join(map(str, e['loc'])) or '<root>'}: {e['msg']}" for e in exc.errors())


def load_experiment(path: Path) -> EvalConfig | TrainConfig:
    try:
        return _EXPERIMENT.validate_python(read_yaml(path))
    except ValidationError as exc:
        raise ConfigError(f"invalid experiment config {path}:\n{_format(exc)}") from exc


def load_dataset_config(path: Path) -> DatasetConfig:
    try:
        return DatasetConfig.model_validate(read_yaml(path))
    except ValidationError as exc:
        raise ConfigError(f"invalid dataset config {path}:\n{_format(exc)}") from exc


def canonical_hash(value: Any) -> str:
    text = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()
