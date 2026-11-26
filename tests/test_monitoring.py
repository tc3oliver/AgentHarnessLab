import json
from pathlib import Path

import pytest

from agent_harness_lab.monitoring import perf, sampler

pytest.importorskip("aiohttp")
from agent_harness_lab.monitoring.proxy import StreamStats


def test_stream_stats_reads_sse_usage_and_first_token():
    stats = StreamStats()
    chunk = lambda body: b"data: " + json.dumps(body).encode() + b"\n\n"  # noqa: E731
    stats.feed(chunk({"choices": [{"delta": {"role": "assistant"}}]}), 1.0)
    stats.feed(chunk({"choices": [{"delta": {"content": "hi"}}]})[:10], 2.0)  # split across reads
    stats.feed(chunk({"choices": [{"delta": {"content": "hi"}}]})[10:], 2.5)
    stats.feed(
        chunk(
            {
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3},
            }
        ),
        3.0,
    )
    stats.feed(b"data: [DONE]\n\n", 3.1)
    stats.finish(3.2, sse=True)
    assert stats.first_token == 2.5
    assert stats.usage == {"prompt_tokens": 7, "completion_tokens": 3}
    assert stats.finish_reason == "stop"
    assert stats.chunks == 3


def test_stream_stats_reads_plain_json():
    stats = StreamStats()
    body = {
        "choices": [{"message": {"tool_calls": [{}]}, "finish_reason": "tool_calls"}],
        "usage": {"prompt_tokens": 1},
    }
    stats.buffer = json.dumps(body, indent=1).encode()
    stats.finish(5.0, sse=False)
    assert (
        stats.first_token == 5.0
        and stats.finish_reason == "tool_calls"
        and stats.usage == {"prompt_tokens": 1}
    )


def test_parse_metrics_sums_labels_and_keeps_known_names():
    text = (
        '# HELP x\nvllm:num_requests_running{model_name="a"} 2.0\n'
        'vllm:num_requests_running{model_name="b"} 1\n'
        'vllm:kv_cache_usage_perc{model_name="a"} 0.25\nvllm:e2e_request_latency_seconds_bucket{le="1"} 3\n'
    )
    assert sampler.parse_metrics(text) == {"num_requests_running": 3.0, "kv_cache_usage_perc": 0.25}


def test_union_of_intervals():
    assert perf._union([(0, 2), (1, 3), (5, 6), (5.5, 5.7)]) == pytest.approx(4.0)


def _write(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def test_analyse_attributes_requests_to_trials(tmp_path):
    trial_dir = tmp_path / "run" / "harbor" / "pi-attempt1" / "task-a__abc"
    trial_dir.mkdir(parents=True)
    (trial_dir / "result.json").write_text(
        json.dumps(
            {
                "trial_name": "task-a__ABC",
                "task_name": "ds/task-a",
                "started_at": "2026-01-01T00:00:00Z",
                "finished_at": "2026-01-01T00:01:40Z",
                "environment_setup": {
                    "started_at": "2026-01-01T00:00:00Z",
                    "finished_at": "2026-01-01T00:00:02Z",
                },
                "agent_execution": {
                    "started_at": "2026-01-01T00:00:02Z",
                    "finished_at": "2026-01-01T00:01:32Z",
                },
                "verifier": {"started_at": "2026-01-01T00:01:32Z", "finished_at": "2026-01-01T00:01:40Z"},
            }
        )
    )
    t0 = perf._ts("2026-01-01T00:00:00Z")
    samples = _write(
        tmp_path / "s.jsonl",
        [
            {
                "kind": "container",
                "t": t0 + 1,
                "event": "seen",
                "id": "c1",
                "name": "task-a__abc-main-1",
                "ip": "10.0.0.5",
            },
            {"kind": "engine", "t": t0 + 10, "num_requests_running": 1, "kv_cache_usage_perc": 0.1},
            {
                "kind": "container",
                "t": t0 + 99,
                "event": "gone",
                "id": "c1",
                "name": "task-a__abc-main-1",
                "ip": "10.0.0.5",
            },
            {
                "kind": "container",
                "t": t0 + 200,
                "event": "seen",
                "id": "c2",
                "name": "other",
                "ip": "10.0.0.5",
            },
        ],
    )
    requests = _write(
        tmp_path / "r.jsonl",
        [
            {
                "client": "10.0.0.5",
                "path": "/v1/chat/completions",
                "start": t0 + 5,
                "first_token": t0 + 6,
                "end": t0 + 16,
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "status": 200,
            },
            {
                "client": "10.0.0.5",
                "path": "/v1/chat/completions",
                "start": t0 + 20,
                "first_token": t0 + 21,
                "end": t0 + 30,
                "prompt_tokens": 300,
                "completion_tokens": 50,
                "status": 200,
            },
            {"client": "10.0.0.5", "path": "/v1/chat/completions", "start": t0 + 210, "end": t0 + 211},
            {"client": "10.0.0.5", "path": "/v1/models", "start": t0 + 3, "end": t0 + 3.1},
        ],
    )
    [row] = perf.analyse(tmp_path / "run", requests, samples)
    assert (row.requests, row.prompt_tokens, row.completion_tokens, row.max_prompt_tokens) == (
        2,
        400,
        250,
        300,
    )
    assert row.model_s == pytest.approx(21.0)
    assert row.agent_s == pytest.approx(90.0) and row.harness_s == pytest.approx(69.0)
    assert row.setup_s == pytest.approx(2.0) and row.verifier_s == pytest.approx(8.0)
    assert row.request_rows[0]["decode_tok_s"] == pytest.approx(20.0)
    assert row.request_rows[0]["kv_cache_usage"] == 0.1
