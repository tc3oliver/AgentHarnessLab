from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agent_harness_lab.core.config import DatasetConfig


@dataclass(frozen=True)
class TaskRef:
    """Identity of a task. Deliberately has no field for tests or reference solutions."""

    task_id: str
    content_hash: str
    instruction_hash: str
    """Whitespace- and case-insensitive, so a repackaged task is still recognised."""
    path: Path
    repository: str | None
    """Canonical `owner/name`, or None when the dataset does not say."""


@dataclass(frozen=True)
class Provenance:
    """Where a dataset came from, for the manifest."""

    source_type: str
    location: str
    """Local path, git URL or Hugging Face repository."""
    revision: str | None
    """Pinned commit; None for local directories."""
    path: str
    license: str | None
    redistributable: bool


@dataclass(frozen=True)
class LoadedDataset:
    config: DatasetConfig
    revision: str
    tasks: tuple[TaskRef, ...]
    provenance: Provenance | None = None


class DatasetLoader(Protocol):
    def load(self, config: DatasetConfig) -> LoadedDataset: ...
