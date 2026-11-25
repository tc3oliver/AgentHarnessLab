"""Read Harbor's per-trial `result.json` (schema 1; 0.25.0 omits the number) and ATIF trajectory."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from agent_harness_lab.core.results import Outcome


class _Timing(BaseModel):
    started_at: datetime | None = None
    finished_at: datetime | None = None


class _Exception(BaseModel):
    exception_type: str
    exception_message: str = ""


class _Verifier(BaseModel):
    rewards: dict[str, float] | None = None


class _Agent(BaseModel):
    n_input_tokens: int | None = None
    n_output_tokens: int | None = None


class _AgentInfo(BaseModel):
    name: str
    version: str


class _TaskId(BaseModel):
    path: Path


class _Step(BaseModel):
    exception_info: _Exception | None = None


class HarborTrial(BaseModel):
    """The fields we use. Other fields are ignored so that Harbor may add some."""

    schema_version: Literal[1] = 1
    trial_name: str
    task_id: _TaskId
    agent_info: _AgentInfo
    agent_result: _Agent | None = None
    verifier_result: _Verifier | None = None
    exception_info: _Exception | None = None
    agent_execution: _Timing | None = None
    finished_at: datetime
    step_results: list[_Step] | None = None

    @property
    def exceptions(self) -> list[_Exception]:
        steps = [s.exception_info for s in self.step_results or [] if s.exception_info]
        return [*([self.exception_info] if self.exception_info else []), *steps]

    @property
    def agent_started(self) -> bool:
        return self.agent_execution is not None or bool(self.step_results)

    @property
    def latency_s(self) -> float | None:
        t = self.agent_execution
        if t is None or t.started_at is None or t.finished_at is None:
            return None
        return max(0.0, (t.finished_at - t.started_at).total_seconds())

    @property
    def observed_version(self) -> str | None:
        return None if self.agent_info.version == "unknown" else self.agent_info.version

    @property
    def tokens(self) -> tuple[int | None, int | None]:
        """Harbor's agents sum missing usage as zero. A real call has prompt tokens, so zero is unknown."""
        if self.agent_result is None or not self.agent_result.n_input_tokens:
            return None, None
        return self.agent_result.n_input_tokens, self.agent_result.n_output_tokens


# Exception names are from harbor/models/trial/error_policy.py in 0.25.0 and 0.27.0.
_TIMEOUT = {"AgentTimeoutError"}
_BUDGET = {
    "ContextWindowExceededError",
    "ContextLengthExceededError",
    "OutputTokenExceededError",
    "OutputLengthExceededError",
}
_REFUSED = {"AgentSafetyRefusalError", "ContentPolicyViolationError"}
_AGENT = {"NonZeroAgentExitCodeError"}
_VERIFIER = {
    "VerifierTimeoutError",
    "RewardFileNotFoundError",
    "RewardFileEmptyError",
    "VerifierOutputParseError",
}
_GRADED = {
    **dict.fromkeys(_TIMEOUT, Outcome.TIMEOUT),
    **dict.fromkeys(_BUDGET, Outcome.BUDGET_EXHAUSTED),
    **dict.fromkeys(_REFUSED, Outcome.FAILED),
    **dict.fromkeys(_AGENT, Outcome.AGENT_ERROR),
}


_EXIT_PREFIX = "Command failed (exit "
"""How Harbor words a non-zero exit. It then picks the exception type by searching the whole output, including
tool output and model text, for phrases such as "rate limit"."""


def _type(exc: _Exception, finished: bool) -> str:
    if finished and exc.exception_message.startswith(_EXIT_PREFIX):
        return "NonZeroAgentExitCodeError"  # the agent was done, so no provider error ended it
    return exc.exception_type


def classify(
    trial: HarborTrial, reward_key: str, threshold: float, *, finished: bool = False
) -> tuple[Outcome, str | None]:
    """Sandbox, provider, Harbor and unknown exceptions are infrastructure errors: visible, but not graded.

    After a graded exception the verifier has the last word: an agent that ran out of time may have solved
    the task. Harbor does the same, except that 0.25.0 does not accept the reward after a non-zero agent exit.
    `finished` means that the agent had ended its turn normally before the exception.
    """
    # One ungraded exception among several decides.
    exc = next(
        (e for e in trial.exceptions if _type(e, finished) not in _GRADED),
        trial.exceptions[0] if trial.exceptions else None,
    )
    kind = _type(exc, finished) if exc else None
    error = f"{exc.exception_type}: {exc.exception_message}" if exc else None
    if exc and not trial.agent_started:  # e.g. installing the harness failed
        return Outcome.INFRA_ERROR, error
    if kind in _VERIFIER:
        return Outcome.VERIFIER_ERROR, error
    if kind is not None and kind not in _GRADED:
        return Outcome.INFRA_ERROR, error
    rewards = trial.verifier_result.rewards if trial.verifier_result else None
    if not rewards or reward_key not in rewards:
        missing = f"verifier returned no '{reward_key}' reward"
        return Outcome.VERIFIER_ERROR, f"{missing}; {error}" if error else missing
    if rewards[reward_key] >= threshold:
        return Outcome.SOLVED, error
    return (Outcome.FAILED if kind is None else _GRADED[kind]), error


def agent_finished(path: Path) -> bool:
    """Whether the trajectory ends with a final answer: text, no tool call and no abnormal stop."""
    try:
        last = json.loads(path.read_text(encoding="utf-8"))["steps"][-1]
        stop = (last.get("extra") or {}).get("stop_reason", "stop")
        return (
            last["source"] == "agent"
            and bool(last.get("message"))
            and not last.get("tool_calls")
            and stop == "stop"
        )
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
        return False


def agent_acted(path: Path) -> bool:
    """Whether the trajectory shows any text or tool call by the agent."""
    try:
        steps = json.loads(path.read_text(encoding="utf-8"))["steps"]
        return any(s["source"] == "agent" and (s.get("message") or s.get("tool_calls")) for s in steps)
    except (OSError, ValueError, KeyError, TypeError):
        return False


def trajectory_counts(path: Path) -> tuple[int | None, int | None]:
    """(tool calls, model calls) from an ATIF trajectory, or unknown.

    OpenCode's subagent tools (`task`, v2 `subagent`) start nested sessions that ATIF omits, so counts would
    be too low. Requests outside the agent loop, such as OpenCode's session title, are not in ATIF either.
    """
    try:
        steps: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["steps"]
        agent = [s for s in steps if s["source"] == "agent" and not s.get("is_copied_context")]
        calls = [c for s in agent for c in s.get("tool_calls") or []]
        if not agent or any(c["function_name"] in {"task", "subagent"} for c in calls):
            return None, None
        model_calls = [s.get("llm_call_count") for s in agent]
    except (OSError, ValueError, KeyError, TypeError):
        return None, None
    if any(not isinstance(n, int) for n in model_calls):
        return len(calls), None
    return len(calls), sum(n for n in model_calls if n is not None)
