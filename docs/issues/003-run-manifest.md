# 003: Remaining manifest fields

Milestone: **v0.1**
Depends on: [001](001-run-harbor-jobs-and-parse-trialresult.md)

## Context

A manifest with commit, dirty flag, seed, config hash, dataset and harness versions and packages already exists (`core/manifest.py`; see [../EXPERIMENTS.md](../EXPERIMENTS.md), Manifest). Real runs need more.

## Scope

Add the Planned fields: adapter file hash, split-file hash, audit-result hash, image digests, per-stack versions, separate seeds, budget counters, hardware summary without host identifiers, command line.

## Acceptance criteria

- Real runs from issue 001 write all Planned fields.
- No secrets or host identifiers appear in a manifest (test).
- Schema version handling is documented.

## Test method

Unit tests on schema and redaction; inspect a manifest from a real smoke run.
