# 006: Baseline evaluations E0 and E1

Milestone: **v0.1**
Depends on: [001](001-run-harbor-jobs-and-parse-trialresult.md), [003](003-run-manifest.md), [004](004-dataset-splits-and-leakage-audit.md), [005](005-vllm-rocm-serving-ladder.md), [019](019-huggingface-and-git-dataset-loaders.md)

## Context

Need Base numbers and a re-measurement of the published Pi adapter before any training claim (../EXPERIMENTS.md).

## Scope

Run Base and the reference Pi adapter under Pi and OpenCode on the validation split, k samples per task, at least 3 repeats. Report infra-error rates. Label results as re-measurement.

## Acceptance criteria

- E0 and E1 reports exist with CIs and infra-error rates.
- A rerun of E0 lands in the first run's interval, or the variance source is explained.
- No test-set run yet.

## Test method

Rerun comparison using the statistics pipeline.
