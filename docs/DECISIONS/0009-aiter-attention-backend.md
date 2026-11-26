# 0009: Use `ROCM_AITER_UNIFIED_ATTN` for evaluation and rollouts

Status: accepted. Date: 2026-11-26. Supersedes [0008](0008-default-attention-backend-for-evaluation.md).

## Context

Decision 0008 kept vLLM's default `ROCM_ATTN` backend until a paired comparison showed whether
`ROCM_AITER_UNIFIED_ATTN` changes task success. That comparison was run on devbench (30 tasks, Pi 1.5.2 and
OpenCode 2.2.7, 3 attempts each, same seed, sampling, images and 1800 s budget; only the backend differs):

| Harness | Default: solved / 90 | AITER: solved / 90 | Paired difference (95% bootstrap CI) | Median agent s, default → AITER |
|---|---|---|---|---|
| Pi | 74 | 75 | +1.1 points [-7.8, +10.0] | 139 → 54 |
| OpenCode | 80 | 78 | -2.2 points [-11.1, +6.7] | 266 → 115 |

Runs: `devbench/runs/devbench-r2` (default) and `devbench-r4-aiter`. Analysis:
`devbench/analysis/devbench-r4-aiter-vs-default.md`. Median decode per request rose from 15.8 to 52.8 tok/s for Pi
and from 8.8 to 20.9 tok/s for OpenCode. The full 180-trial run took 4 h 22 min, against 6 h 46 min.

## Decision

Evaluation and RL rollouts on vLLM 0.33.0 ROCm with Qwen3.8-27B use `--attention-backend ROCM_AITER_UNIFIED_ATTN`
from 2026-11-26 (`devbench-r4-aiter` onward). Earlier runs used the default backend. Results from the two backends are not mixed in one comparison without saying so; `devbench-r2` stays the default-backend
reference.

## Consequences

- Runs are about 2.4 times faster, so wall-clock budgets now bind later. Runs on the old backend are a separate
  series.
- The difference is within noise on a set where 19-23 of 30 tasks are saturated. A small quality effect cannot be
  excluded; recheck it when devbench has more hard tasks.
- Revisit this decision when vLLM or the model changes.
