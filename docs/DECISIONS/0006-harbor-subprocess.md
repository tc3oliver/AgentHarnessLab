# 0006: Run Harbor as a subprocess

Status: accepted. Date: 2026-11-25.

## Context

OpenEnv caps Harbor below 0.26, so training needs 0.25.0. OpenCode v2 needs the `opencode-v2` agent, present in 0.27.0 and
absent from 0.25.0. Both cannot be installed in one environment.

## Decision

`runner.command` names a Harbor executable, which may live in its own environment, and `runner.version` must match what
`--version` reports. Only versions with recorded fixtures are accepted. We read Harbor's JSON files with a small model of
our own instead of importing Harbor.

## Consequences

One installation of this package can evaluate with several Harbor versions, and Harbor's dependencies never conflict with
ours. 0.25.0 stays the default. Results from different Harbor versions are not comparable: `compare` refuses them.
Adding a Harbor version means recording fixtures and extending `SUPPORTED_HARBOR` and each adapter's `harbor_versions`.
