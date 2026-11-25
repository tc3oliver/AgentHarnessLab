# 0005: Planned features fail before any work, and simulated data is labelled

Status: accepted. Date: 2026-11-25.

## Context

A skeleton that accepts a training config and prints something plausible would mislead users.

## Decision

Planned features raise `FeatureNotImplementedError` (exit code 3) before writing files. Every result and manifest carries `simulated`; reports and comparisons of simulated runs start with a banner, and simulated and real runs cannot be compared.

## Consequences

`baseline.yaml` and `joint_rl.yaml` validate but do not run. Contributors must replace the error with a tested implementation, not a stub.
