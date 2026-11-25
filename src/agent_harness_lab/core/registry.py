"""Name -> factory registries. Third-party packages add entries through entry points, e.g.

    [project.entry-points."agent_harness_lab.harness"]
    my-agent = "my_package:MyHarness"

Built-ins are import strings, so listing or using one plugin never imports another's dependencies.
"""

from __future__ import annotations

from importlib import import_module
from importlib.metadata import entry_points
from typing import Any

from agent_harness_lab.errors import ConfigError


class Registry:
    def __init__(self, kind: str, builtin: dict[str, str]) -> None:
        self.kind = kind
        self._builtin = builtin

    def _external(self) -> dict[str, Any]:
        return {ep.name: ep for ep in entry_points(group=f"agent_harness_lab.{self.kind}")}

    def names(self) -> list[str]:
        return sorted({*self._builtin, *self._external()})

    def get(self, name: str) -> Any:
        if name in self._builtin:  # built-ins cannot be shadowed
            module, _, attribute = self._builtin[name].partition(":")
            return getattr(import_module(module), attribute)
        external = self._external()
        if name in external:
            return external[name].load()
        raise ConfigError(f"unknown {self.kind} '{name}'; available: {', '.join(self.names())}")


_PKG = "agent_harness_lab"
HARNESSES = Registry(
    "harness",
    {
        "oracle": f"{_PKG}.harness.harbor:OracleHarness",
        "nop": f"{_PKG}.harness.harbor:NopHarness",
        "opencode-v2": f"{_PKG}.harness.harbor:OpenCodeV2Harness",
        "pi": f"{_PKG}.harness.harbor:PiHarness",
        "opencode": f"{_PKG}.harness.harbor:OpenCodeHarness",
    },
)
DATASETS = Registry(
    "dataset",
    {
        "local": f"{_PKG}.dataset.loaders:LocalDataset",
        "huggingface": f"{_PKG}.dataset.loaders:HuggingFaceDataset",
        "git": f"{_PKG}.dataset.loaders:GitDataset",
    },
)
RUNNERS = Registry(
    "runner",
    {
        "mock": f"{_PKG}.evaluation.runners:MockRunner",
        "harbor": f"{_PKG}.evaluation.harbor:HarborRunner",
    },
)
TRAINERS = Registry("trainer", {"trl": f"{_PKG}.training.backends:TrlBackend"})
