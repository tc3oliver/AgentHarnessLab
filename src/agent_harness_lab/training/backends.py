from __future__ import annotations

from pathlib import Path

from agent_harness_lab.core.config import TrainConfig
from agent_harness_lab.errors import FeatureNotImplementedError


class TrlBackend:
    """Will drive TRL's `HarnessAsyncGRPOTrainer`. GRPO itself is not reimplemented here."""

    def train(self, config: TrainConfig) -> Path:
        joint = len(config.harnesses) > 1
        raise FeatureNotImplementedError(
            "joint multi-harness RL" if joint else "single-harness RL", "v0.3" if joint else "v0.2"
        )
