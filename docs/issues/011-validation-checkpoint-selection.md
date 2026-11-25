# 011: Checkpoint selection on validation only

Milestone: **v0.2**
Depends on: [004](004-dataset-splits-and-leakage-audit.md), [007](007-statistics-and-report.md)

## Context

The reference recipe selected on benchmark tasks (../RESEARCH.md, Confounders).

## Scope

Add periodic validation evaluation during training and a selection rule fixed in config. Block selection from reading test splits.

## Acceptance criteria

- Config with a test split in selection is rejected.
- Selected and final checkpoints both saved and reported.

## Test method

Unit test for the guard; integration on a tiny loop.
