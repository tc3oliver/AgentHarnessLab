from __future__ import annotations

from typing import Any, Protocol

from agent_harness_lab.core.config import HarnessConfig, InferenceConfig, ModelConfig


class HarnessAdapter(Protocol):
    """Describes one unmodified agent harness. It never implements an agent loop."""

    name: str
    harbor_versions: frozenset[str]
    """Harbor versions this adapter was checked against."""

    def harbor_agent(
        self, harness: HarnessConfig, model: ModelConfig, inference: InferenceConfig
    ) -> dict[str, Any]:
        """Return the fields of a Harbor `AgentConfig`. Raise `ConfigError` for unsupported options."""
        ...
