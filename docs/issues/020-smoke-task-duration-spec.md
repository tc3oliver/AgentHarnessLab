# 020: ahl-fix-duration-parse tests more than it states

Milestone: **v0.1**
Depends on: none

## Context

The hidden test expects `ValueError` for `1.5h`; the instruction does not say that decimals are invalid. On 2026-11-25 this
task failed in 9 of 10 Qwen3.8-27B trials (data in [../reports/data](../reports/data)); all nine failed on `1.5h`.
The results were kept as failures.

## Scope

State in `instruction.md` that numbers are non-negative integers. This changes the task hash, so results before and after are not comparable.

## Acceptance criteria

- Oracle 12/12, nop 0/12.
- The README of the smoke tasks notes the change.

## Test method

`pytest -m docker -k smoke`.
