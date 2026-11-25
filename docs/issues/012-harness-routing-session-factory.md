# 012: Harness routing session factory

Milestone: **v0.3**
Depends on: [009](009-single-harness-grpo-pi.md)

## Context

TRL passes only `prompt` and `seed=group_id` to the session factory; `HarborSessionFactory` holds one harness; `group_id` restarts on resume (../UPSTREAM.md, Reusable pieces).

## Scope

Implement a factory that routes each rollout to Pi or OpenCode by an explicit field carried with the row, not by `seed % n`. Each task appears once per harness so groups are Task x Harness. If TRL cannot carry the field, propose a minimal upstream change or a wrapper (decide and record).

## Acceptance criteria

- Routing is correct across a checkpoint resume (test).
- Each group is single-harness and Task x Harness.
- Ratio of harnesses follows config.

## Test method

Unit tests with fake sessions; resume test.
