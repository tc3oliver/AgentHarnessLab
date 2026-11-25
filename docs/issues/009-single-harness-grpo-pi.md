# 009: Single-harness GRPO under Pi (E2)

Milestone: **v0.2**
Depends on: [006](006-baseline-evaluations-e0-e1.md)

## Context

First training run. Reference recipe: LoRA r=32, 8 rollouts per task, 2x B200 (../UPSTREAM.md, Reference work). Training stack versions conflict (Constraints 1-3).

## Scope

Set up TRL async GRPO with OpenEnv Harbor rollouts under Pi, using our own data split. Log rewards, rows and supervised tokens per step. Use full-vocabulary sampling.

## Acceptance criteria

- Tiny loop passes (ladder rungs 4-6), then a full run completes.
- Logs include rollouts and supervised tokens.
- Validation pass@1 vs Base reported with CI.

## Test method

Ladder rungs 4-7; validation evaluation via issue 001 runner.
