# 001: Run Harbor jobs (Pi and OpenCode) from an experiment config and parse TrialResult into the result schema

Milestone: **v0.1**
Depends on: none

## Context

The mock runner and schemas exist; nothing runs a real harness. Harbor 0.25.0 is the pinned version (see ../UPSTREAM.md, Constraints 1). Each trial writes a `result.json` (`TrialResult`).

## Scope

Build a runner that takes an experiment config (model endpoint, dataset, split, harness `pi` or `opencode`, k, limits), builds a Harbor `JobConfig` (`AgentConfig` with `base_url`, `model_api_key_name`, `model_api_format`, `kwargs`), runs the job, and converts each `TrialResult` to the project result schema. Map outcomes by the rules in ../EXPERIMENTS.md. Do not read secret values; pass key env var names only.

## Acceptance criteria

- Oracle and nop smoke tasks run through the same code path and parse correctly.
- A Pi and an OpenCode trial against a real endpoint each produce a schema-valid record (status Verified only once run).
- Outcome mapping covers solved, failed, timeout, budget, infra_error; infra errors are excluded from pass@1 but counted.
- Missing tokens, cost or tool calls are null, never 0.
- Unit tests on recorded `result.json` fixtures cover each outcome.

## Test method

Unit tests with fixture result files; smoke run with oracle/nop; one real trial per harness on the validation ladder rung 2.
