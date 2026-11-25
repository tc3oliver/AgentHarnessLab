# 014: Joint multi-harness training run (E3)

Milestone: **v0.3**
Depends on: [012](012-harness-routing-session-factory.md), [013](013-per-harness-logging-and-weights.md), [010](010-lora-update-path-rocm.md), [011](011-validation-checkpoint-selection.md)

## Context

First shared-LoRA run on Pi and OpenCode.

## Scope

Run a small Joint training with the routing factory; evaluate on validation under both harnesses.

## Acceptance criteria

- Run completes; both harnesses contribute rollouts.
- Validation results per harness with CIs; null results reported.
- Go/no-go note for v0.4 written.

## Test method

Ladder rung 7 on the joint config; validation evaluation.
