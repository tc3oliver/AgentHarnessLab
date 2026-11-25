# 018: Qwen3.8-Flash-Next feasibility and reduced benchmark

Milestone: **v0.5**
Depends on: [016](016-matched-budget-multiseed-benchmark.md)

## Context

Gated model; vLLM supports it, TRL lacks `qwen4_exp` (../UPSTREAM.md, Constraint 6).

## Scope

Check access and licence terms, serve on target hardware, decide trainer path (TRL support, port, or other), run a reduced E4 or an evaluation-only study if training is not possible.

## Acceptance criteria

- Serving passes ladder rungs 0-3.
- Training path decision recorded with evidence.
- Reduced comparison reported, or a documented stop.

## Test method

Ladder rungs repeated for this model.
