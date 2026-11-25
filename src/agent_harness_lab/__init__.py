"""AgentHarnessLab: reproducible cross-harness agent post-training."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("agent-harness-lab")
except PackageNotFoundError:  # running from a source tree that is not installed
    __version__ = "0.0.0+unknown"
