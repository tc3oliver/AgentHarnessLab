"""Pi and OpenCode through Harbor. Not implemented: docs/issues/ holds the first integration issue."""

from __future__ import annotations

from typing import Any

from agent_harness_lab.core.config import HarnessConfig, InferenceConfig, ModelConfig
from agent_harness_lab.errors import FeatureNotImplementedError


class _HarborHarness:
    name: str

    def harbor_agent(
        self, harness: HarnessConfig, model: ModelConfig, inference: InferenceConfig
    ) -> dict[str, Any]:
        raise FeatureNotImplementedError(f"Harbor agent configuration for '{self.name}'", "v0.1")


class PiHarness(_HarborHarness):
    name = "pi"


class OpenCodeHarness(_HarborHarness):
    """OpenCode v1 (`opencode-ai`). Harbor 0.25.0 has no OpenCode v2 agent."""

    name = "opencode"
