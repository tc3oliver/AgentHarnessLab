"""Join the proxy request log and the sampler log with Harbor trials.

A request belongs to the trial whose container had the request's client address while the request ran. Per
trial this gives model time (union of request intervals: the time the engine worked for the trial, used as GPU
time), harness/tool time (agent execution minus model time) and token counts as the engine counted them. Per
request it gives decode throughput next to output length, context length, concurrency and KV-cache usage, so a
slow trial can be attributed to inference or to tool execution.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


def _ts(value: str | None) -> float | None:
    return None if value is None else datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def _jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


@dataclass
class Trial:
    trial_name: str
    task: str
    harness_dir: str
    started: float
    finished: float
    agent_started: float | None
    agent_finished: float | None
    setup_s: float | None
    verifier_s: float | None


@dataclass
class TrialPerf:
    trial_name: str
    task: str
    harness_dir: str
    container: str | None
    requests: int = 0
    model_s: float = 0.0
    """Union of request intervals: wall time in which the engine was serving this trial."""
    agent_s: float | None = None
    harness_s: float | None = None
    """Agent execution time not covered by a model request: tool execution and harness overhead."""
    setup_s: float | None = None
    verifier_s: float | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    max_prompt_tokens: int = 0
    errors: int = 0
    request_rows: list[dict[str, Any]] = field(default_factory=list)


def load_trials(run_dir: Path) -> list[Trial]:
    trials = []
    for path in sorted(run_dir.glob("harbor/*/*/result.json")):
        data = json.loads(path.read_text())
        if "trial_name" not in data:
            continue

        def span(key: str, data: dict[str, Any] = data) -> tuple[float | None, float | None]:
            part = data.get(key) or {}
            return _ts(part.get("started_at")), _ts(part.get("finished_at"))

        setup = span("environment_setup")
        agent = span("agent_execution")
        verifier = span("verifier")
        started, finished = _ts(data.get("started_at")), _ts(data.get("finished_at"))
        if started is None or finished is None:
            continue
        trials.append(
            Trial(
                trial_name=data["trial_name"],
                task=str(data.get("task_name", "")).rsplit("/", 1)[-1],
                harness_dir=path.parent.parent.name,
                started=started,
                finished=finished,
                agent_started=agent[0],
                agent_finished=agent[1],
                setup_s=None if None in setup else setup[1] - setup[0],  # type: ignore[operator]
                verifier_s=None if None in verifier else verifier[1] - verifier[0],  # type: ignore[operator]
            )
        )
    return trials


def containers(samples: Iterable[dict[str, Any]]) -> dict[str, list[tuple[str, float, float]]]:
    """IP -> [(container name, first seen, last seen)], from the sampler's container events."""
    open_: dict[str, tuple[str, str, float]] = {}
    spans: dict[str, list[tuple[str, float, float]]] = {}
    for row in samples:
        if row.get("kind") != "container":
            continue
        if row["event"] == "seen":
            open_[row["id"]] = (row["name"], row["ip"], row["t"])
        elif row["id"] in open_:
            name, ip, first = open_.pop(row["id"])
            spans.setdefault(ip, []).append((name, first, row["t"]))
    for name, ip, first in open_.values():
        spans.setdefault(ip, []).append((name, first, float("inf")))
    return spans


def _owner(
    spans: dict[str, list[tuple[str, float, float]]], ip: str | None, t: float, slack: float
) -> str | None:
    for name, first, last in spans.get(ip or "", []):
        if first - slack <= t <= last + slack:
            return name
    return None


def _union(intervals: list[tuple[float, float]]) -> float:
    total, end = 0.0, float("-inf")
    for start, stop in sorted(intervals):
        if stop <= end:
            continue
        total += stop - max(start, end)
        end = stop
    return total


class EngineSeries:
    """Nearest engine sample (requests running/waiting, KV-cache usage) at a time."""

    def __init__(self, samples: Iterable[dict[str, Any]]) -> None:
        rows = sorted(
            (r for r in samples if r.get("kind") == "engine" and "error" not in r), key=lambda r: r["t"]
        )
        self.times = [r["t"] for r in rows]
        self.rows = rows

    def at(self, t: float) -> dict[str, Any]:
        if not self.rows:
            return {}
        i = bisect.bisect_left(self.times, t)
        candidates = [j for j in (i - 1, i) if 0 <= j < len(self.rows)]
        return self.rows[min(candidates, key=lambda j: abs(self.times[j] - t))]


def request_row(request: dict[str, Any], engine: EngineSeries) -> dict[str, Any]:
    first, end = request.get("first_token"), request["end"]
    completion = request.get("completion_tokens")
    decode_s = None if first is None else end - first
    sample = engine.at((request["start"] + end) / 2)
    return {
        "start": request["start"],
        "ttft_s": None if first is None else first - request["start"],
        "duration_s": end - request["start"],
        "decode_s": decode_s,
        "prompt_tokens": request.get("prompt_tokens"),
        "completion_tokens": completion,
        "decode_tok_s": completion / decode_s if completion and decode_s and decode_s > 0.05 else None,
        "in_flight_at_start": request.get("in_flight_at_start"),
        "engine_running": sample.get("num_requests_running"),
        "engine_waiting": sample.get("num_requests_waiting"),
        "kv_cache_usage": sample.get("kv_cache_usage_perc", sample.get("gpu_cache_usage_perc")),
        "finish_reason": request.get("finish_reason"),
        "error": request.get("error"),
    }


def analyse(run_dir: Path, requests_log: Path, samples_log: Path, slack: float = 5.0) -> list[TrialPerf]:
    trials = load_trials(run_dir)
    samples = list(_jsonl(samples_log))
    spans = containers(samples)
    engine = EngineSeries(samples)
    by_name = {t.trial_name.lower(): t for t in trials}
    perf = {
        t.trial_name: TrialPerf(
            t.trial_name, t.task, t.harness_dir, None, setup_s=t.setup_s, verifier_s=t.verifier_s
        )
        for t in trials
    }
    intervals: dict[str, list[tuple[float, float]]] = {name: [] for name in perf}
    for request in _jsonl(requests_log):
        if request.get("path", "").rstrip("/").split("/")[-1] not in ("completions", "responses", "messages"):
            continue
        container = _owner(spans, request.get("client"), request["start"], slack)
        trial = next((t for key, t in by_name.items() if container and key in container.lower()), None)
        if trial is None:
            continue
        p = perf[trial.trial_name]
        p.container = container
        p.requests += 1
        p.errors += bool(request.get("error")) or (request.get("status") or 200) >= 400
        p.prompt_tokens += request.get("prompt_tokens") or 0
        p.completion_tokens += request.get("completion_tokens") or 0
        p.cached_tokens += request.get("cached_tokens") or 0
        p.max_prompt_tokens = max(p.max_prompt_tokens, request.get("prompt_tokens") or 0)
        intervals[trial.trial_name].append((request["start"], request["end"]))
        p.request_rows.append(request_row(request, engine))
    for trial in trials:
        p = perf[trial.trial_name]
        p.model_s = _union(intervals[trial.trial_name])
        if trial.agent_started is not None and trial.agent_finished is not None:
            p.agent_s = trial.agent_finished - trial.agent_started
            p.harness_s = max(0.0, p.agent_s - p.model_s)
    return list(perf.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("-o", "--output", type=Path, required=True, help="JSON lines, one per trial")
    args = parser.parse_args()
    rows = analyse(args.run_dir, args.requests, args.samples)
    with args.output.open("w", encoding="utf-8") as out:
        for row in rows:
            out.write(json.dumps(asdict(row)) + "\n")
    matched = sum(r.requests > 0 for r in rows)
    print(f"{len(rows)} trials, {matched} with matched requests, {sum(r.requests for r in rows)} requests")


if __name__ == "__main__":
    main()
