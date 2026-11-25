# 0001: Modular monolith with entry-point plugins

Status: accepted. Date: 2026-11-25.

## Context

The project needs replaceable harnesses, datasets, runners and trainers, but has one user-facing process.

## Decision

One Python package. Interfaces are `typing.Protocol`s. A registry maps names to import strings for built-ins and to entry points (`agent_harness_lab.harness`, `.dataset`, `.runner`, `.trainer`) for third parties. No database, web UI, Kubernetes or services.

## Consequences

Heavy dependencies (Harbor, TRL, vLLM) are never imported to run another plugin. External plugins can be selected for harnesses today; new dataset source, runner and trainer *types* also need a config schema entry, because config types are closed unions. We accept that until a third party needs it.
