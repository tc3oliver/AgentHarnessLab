"""Repository-level train/validation split (docs/DATASETS.md, split rules)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator

from agent_harness_lab.core.config import canonical_hash
from agent_harness_lab.dataset.base import LoadedDataset
from agent_harness_lab.dataset.loaders import tasks_hash
from agent_harness_lab.errors import ConfigError


class SplitPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_ids: list[str]
    repositories: list[str]


class SplitFile(BaseModel):
    """Immutable record of a split. `hash` covers every other field, so an edited file fails to load."""

    model_config = ConfigDict(extra="forbid")

    dataset: str
    revision: str
    tasks_hash: str
    seed: int
    validation_fraction: float
    train: SplitPart
    validation: SplitPart
    hash: str = ""

    def _digest(self) -> str:
        return "sha256:" + canonical_hash(self.model_dump(mode="json", exclude={"hash"}))

    @model_validator(mode="after")
    def _check_hash(self) -> SplitFile:
        if self.hash and self.hash != self._digest():
            raise ValueError("split file hash does not match its content")
        return self

    def sealed(self) -> SplitFile:
        return self.model_copy(update={"hash": self._digest()})

    def write(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> SplitFile:
        try:
            return cls.model_validate_json(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ConfigError(f"invalid split file {path}: {exc}") from exc


def _in_validation(repository: str, fraction: float, seed: int) -> bool:
    digest = hashlib.sha256(f"{seed}:{repository}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64 < fraction


def split_by_repository(dataset: LoadedDataset, validation_fraction: float, seed: int) -> SplitFile:
    """Assign whole repositories to train or validation by a seeded hash of the repository name.

    Each repository is decided on its own, so the share of validation tasks only approximates the fraction.
    A task without a repository cannot be placed safely, so any such task is an error.
    """
    if not 0 < validation_fraction < 1:
        raise ConfigError("validation fraction must be between 0 and 1, exclusive")
    unplaced = [t.task_id for t in dataset.tasks if t.repository is None]
    if unplaced:
        raise ConfigError(
            f"{len(unplaced)} of {len(dataset.tasks)} tasks declare no repository "
            f"(e.g. {', '.join(unplaced[:5])}); a repository-level split needs one for every task"
        )
    parts: dict[bool, SplitPart] = {
        False: SplitPart(task_ids=[], repositories=[]),
        True: SplitPart(task_ids=[], repositories=[]),
    }
    for repository in sorted({t.repository for t in dataset.tasks if t.repository}):
        parts[_in_validation(repository, validation_fraction, seed)].repositories.append(repository)
    validation = set(parts[True].repositories)
    for task in sorted(dataset.tasks, key=lambda t: t.task_id):
        parts[task.repository in validation].task_ids.append(task.task_id)
    if not parts[False].task_ids or not parts[True].task_ids:
        raise ConfigError("one split is empty; change the seed or the validation fraction")
    return SplitFile(
        dataset=dataset.config.name,
        revision=dataset.revision,
        tasks_hash=tasks_hash(dataset.tasks),
        seed=seed,
        validation_fraction=validation_fraction,
        train=parts[False],
        validation=parts[True],
    ).sealed()
