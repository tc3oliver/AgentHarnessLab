from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_harness_lab.core.config import InferenceConfig


@dataclass(frozen=True)
class EndpointInfo:
    served_models: tuple[str, ...]
    engine_version: str | None


class InferenceBackend(Protocol):
    """Read-only view of a running OpenAI-compatible server. Harnesses send the completions, not us."""

    def probe(self, config: InferenceConfig) -> EndpointInfo:
        """Raise `RunError` when the server is unreachable or does not answer like an OpenAI server."""
        ...
