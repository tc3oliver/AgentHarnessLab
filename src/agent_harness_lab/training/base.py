from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from agent_harness_lab.core.config import TrainConfig


class TrainingBackend(Protocol):
    def train(self, config: TrainConfig) -> Path:
        """Run training and return the adapter directory."""
        ...


class AdapterMerger(Protocol):
    """No implementation exists yet (planned for v0.4, on PEFT `add_weighted_adapter`)."""

    def merge(self, adapters: Sequence[Path], weights: Sequence[float], output: Path) -> Path: ...
