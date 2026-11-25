# 0004: Advantage groups are Task x Harness

Status: accepted, not implemented (v0.3). Date: 2026-11-25.

## Context

GRPO compares rewards within a group. Mixing harnesses in a group makes the advantage partly measure the harness. TRL standardises within one dataset row, so one row per (task, harness) already gives the wanted groups.

## Decision

Joint training repeats each task once per harness and routes every row to its harness. No GRPO code is changed. `Trajectory.group` encodes the rule. Mixed-harness groups are an ablation, not the default.

## Consequences

TRL passes only `prompt` and `seed=group_id` to the session factory and `HarborSessionFactory` holds one harness, so a routing factory is needed. Routing on `seed % n` breaks on resume, because `group_id` restarts at 0 while the row position does not. The route must be recoverable from the row itself. Harnesses that rewrite history yield more training rows per rollout; rows and supervised tokens per harness must be logged.
