# 008: Extract efficiency fields from Harbor and ATIF; GPU-hour pricing

Milestone: **v0.1**
Depends on: [001](001-run-harbor-jobs-and-parse-trialresult.md)

## Context

Aggregation of tokens, tool calls, latency and cost per solved task exists (`evaluation/metrics.py`), with n/a for incomplete columns. Real trials must supply the inputs ([../EXPERIMENTS.md](../EXPERIMENTS.md), Metrics).

## Scope

Extract tokens from `agent_result`, tool calls from the ATIF trajectory when present, latency from phase timings. Add a configurable local price model (per token or per GPU-hour) so cost exists for local models, recorded in the manifest.

## Acceptance criteria

- Fixture trajectories with known counts give those counts.
- Harnesses that do not report a field give null, not 0.
- Cost per solved task includes failed, retried and infrastructure-error trials.
- Tool-call counting is documented per harness.

## Test method

Fixture trajectories and result files; unit tests.
