"""The shipped harness configs load and map to the Harbor agent options they promise."""

from pathlib import Path

import pytest

from agent_harness_lab.core.config import HarnessConfig, InferenceConfig, ModelConfig, read_yaml
from agent_harness_lab.harness.harbor import OpenCodeV2Harness, PiHarness

CONFIGS = Path(__file__).resolve().parents[1] / "configs" / "harnesses"
MODEL = ModelConfig(id="Qwen/Qwen3.8-27B", revision="37561816e66b5b9153b1b64c10968c18c1e6f4a0")
INFERENCE = InferenceConfig(backend="vllm", base_url="http://127.0.0.1:8100/v1", api_key_env="KEY")


def agent(name: str, harness: type) -> dict:
    config = HarnessConfig(**read_yaml(CONFIGS / name))
    return harness().harbor_agent(config, MODEL, INFERENCE)


def test_opencode_v2_noweb_denies_web_tools() -> None:
    assert agent("opencode-v2-noweb.yaml", OpenCodeV2Harness)["kwargs"] == {
        "version": "2.2.7",
        "disable_web_search": True,
    }


def test_opencode_v2_unchanged_for_reproduction() -> None:
    assert agent("opencode-v2.yaml", OpenCodeV2Harness)["kwargs"] == {"version": "2.2.7"}


@pytest.mark.parametrize("name", sorted(p.name for p in CONFIGS.glob("pi*.yaml")))
def test_pi_configs_load(name: str) -> None:
    assert agent(name, PiHarness)["kwargs"]["version"]
