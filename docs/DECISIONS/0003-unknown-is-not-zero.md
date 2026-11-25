# 0003: Unknown values stay unknown; infrastructure errors are not failures

Status: accepted. Date: 2026-11-25.

## Context

Harnesses report different usage fields, and sandbox failures are common. Counting a missing token count as zero flatters an arm; counting a sandbox crash as a failure punishes it at random.

## Decision

Unreported values are `null`, and any aggregate over a column with a null is `n/a`. Outcomes are `solved`, `failed`, `timeout`, `budget_exhausted` (all graded) and `infra_error` (excluded from pass@1, always counted in reports). Comparisons use only trials graded on both sides and report how many were dropped.

## Consequences

Some cells show `n/a` until harness telemetry is complete. A run with many infrastructure errors is visible but not rejected; EXPERIMENTS.md sets the limit for a reportable run.
