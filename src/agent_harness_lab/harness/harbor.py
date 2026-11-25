"""Harbor agent configurations. Harbor installs and drives the unmodified harness."""

from __future__ import annotations

from typing import Any

from agent_harness_lab.core.config import HarnessConfig, InferenceConfig, ModelConfig
from agent_harness_lab.errors import ConfigError


class _Control:
    """Oracle replays the reference solution; nop does nothing. They test the pipeline, not models."""

    name: str
    harbor_versions = frozenset({"0.25.0", "0.27.0"})

    def harbor_agent(
        self, harness: HarnessConfig, model: ModelConfig, inference: InferenceConfig
    ) -> dict[str, Any]:
        if harness.options or harness.max_turns is not None:
            raise ConfigError(f"harness '{self.name}' takes no options or max_turns")
        return _timeout({"name": self.name}, harness)


class OracleHarness(_Control):
    name = "oracle"


class NopHarness(_Control):
    name = "nop"


def _timeout(agent: dict[str, Any], harness: HarnessConfig) -> dict[str, Any]:
    if harness.timeout_s is not None:
        agent["override_timeout_sec"] = harness.timeout_s
    if harness.setup_timeout_s is not None:
        agent["override_setup_timeout_sec"] = harness.setup_timeout_s
    return agent


class _Installed:
    name: str
    harbor_versions: frozenset[str]
    allowed_options: frozenset[str]
    """Harbor options that are plain values. Paths are excluded: file contents are not in the manifest."""
    supports_max_turns = False
    provider = "agentlab"
    """Model name prefix. OpenCode uses it as its own provider id; `openai` there means the Responses API."""

    def harbor_agent(
        self, harness: HarnessConfig, model: ModelConfig, inference: InferenceConfig
    ) -> dict[str, Any]:
        if unknown := sorted(harness.options.keys() - self.allowed_options):
            raise ConfigError(f"harness '{self.name}': unsupported options: {', '.join(unknown)}")
        if harness.max_turns is not None and not self.supports_max_turns:
            raise ConfigError(f"harness '{self.name}' has no max_turns option in Harbor; use timeout_s")
        if inference.api_key_env is None:
            raise ConfigError(
                f"harness '{self.name}' needs inference.api_key_env: Harbor takes a key only by variable name"
            )
        served = inference.served_model or model.id
        agent: dict[str, Any] = {
            "name": self.name,
            "model_name": f"{self.provider}/{served}",
            "base_url": inference.agent_base_url or inference.base_url,
            "model_api_key_name": inference.api_key_env,
            "model_api_format": "openai_chat_completions",
            "kwargs": {"version": harness.version, **harness.options},
        }
        if harness.max_turns is not None:
            agent["kwargs"]["max_turns"] = harness.max_turns
        return _timeout(agent, harness)


class PiHarness(_Installed):
    name = "pi"
    # Harbor only strips a provider that LiteLLM knows; otherwise Pi would send the prefix to the server.
    provider = "openai"
    harbor_versions = frozenset({"0.25.0", "0.27.0"})
    supports_max_turns = True
    allowed_options = frozenset({"reasoning_effort"})


class OpenCodeHarness(_Installed):
    """OpenCode 1.x (`opencode-ai`)."""

    name = "opencode"
    allowed_options = frozenset({"variant", "disable_web_search"})
    harbor_versions = frozenset({"0.25.0", "0.27.0"})


class OpenCodeV2Harness(_Installed):
    """OpenCode 2.x (`@opencode/cli`). Harbor 0.25.0 has no such agent and OpenEnv cannot capture it."""

    name = "opencode-v2"
    allowed_options = frozenset({"variant", "disable_web_search", "codemode"})
    harbor_versions = frozenset({"0.27.0"})
