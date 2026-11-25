# 007: Bootstrap intervals, Holm correction and k-sample scores

Milestone: **v0.1**
Depends on: none

## Context

The exact sign test, paired comparison and Markdown report exist (`evaluation/compare.py`). Decision rules in [../RESEARCH.md](../RESEARCH.md) also need intervals and multiplicity control.

## Scope

Add paired bootstrap CIs (10,000 resamples, seeds as clusters when 3 or more), Holm correction across primary tests, per-task averaging over k samples, and reporting of discordant counts with CIs first.

## Acceptance criteria

- Known-answer tests pass on hand-computed cases.
- Report states 'inconclusive' when the CI spans the decision margin.
- No ranking of arms with fewer than 3 seeds.
- Permuting task order does not change results (property test).

## Test method

Unit tests with fixed inputs and expected outputs.
