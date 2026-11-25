# 013: Per-harness logging and row-weight controls

Milestone: **v0.3**
Depends on: [009](009-single-harness-grpo-pi.md)

## Context

History rewriting and compaction can over-weight one harness in a joint loss (../UPSTREAM.md, Constraints 9-10).

## Scope

Log rows and supervised tokens per harness per step. Add an optional per-harness normalisation for sensitivity runs.

## Acceptance criteria

- Per-harness counts appear in logs and manifest.
- Normalisation off by default; on changes the weights as unit tests expect.

## Test method

Unit tests with synthetic rollouts forking into several rows.
