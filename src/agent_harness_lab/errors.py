"""Expected failures. Each class maps to one CLI exit code; anything else is a bug and keeps its traceback."""


class AgentLabError(Exception):
    exit_code = 1


class ConfigError(AgentLabError):
    exit_code = 2


class FeatureNotImplementedError(AgentLabError):
    """The feature is planned. Raised before any work starts, so no partial output is left."""

    exit_code = 3

    def __init__(self, feature: str, milestone: str) -> None:
        super().__init__(f"{feature} is not implemented (planned for {milestone}; see docs/ROADMAP.md)")


class RunError(AgentLabError):
    exit_code = 4


class ComparisonError(AgentLabError):
    exit_code = 5


class LeakageError(AgentLabError):
    exit_code = 6
