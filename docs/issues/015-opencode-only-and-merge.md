# 015: OpenCode-only specialist and adapter merge

Milestone: **v0.4**
Depends on: [014](014-joint-training-run.md)

## Context

Needed for arms OpenCode-only and Merge (../RESEARCH.md, Arms).

## Scope

Train the OpenCode-only specialist at the same budget rules; implement merging via PEFT with the weight grid fixed in config and chosen on validation only.

## Acceptance criteria

- Specialist trained with budget counters logged.
- Merge chosen on validation; test untouched.
- Budget accounting shows Merge consumes both specialists' budget.

## Test method

Budget-audit script; unit test on merge config validation.
