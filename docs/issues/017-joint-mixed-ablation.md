# 017: Joint-mixed group ablation

Milestone: **v0.4**
Depends on: [014](014-joint-training-run.md), [007](007-statistics-and-report.md)

## Context

Isolates whether per-harness advantage matters (../RESEARCH.md, Arms).

## Scope

Implement groups that mix harnesses and standardise advantage across them; run at the same budget.

## Acceptance criteria

- Ablation run completes at matched budget.
- Result compared to Joint with paired CI.

## Test method

Unit test of advantage computation; benchmark run.
