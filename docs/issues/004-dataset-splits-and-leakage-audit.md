# 004: Dataset splits and leakage audit

Milestone: **v0.1**
Depends on: none

## Context

Split and audit rules are in ../DATASETS.md. TermGrade has no repository field; scale800 licence is undeclared.

## Scope

The audit core exists in `src/agent_harness_lab/dataset/audit.py` (exact and normalised-instruction hash, declared repository, canary strings, non-train split; local datasets only). Remaining: write the scale800 name-to-repository mapping (task directory names such as `owner__repo.<commit>...` are the only source; `task.toml` has no repository field), then implement repository-level split files (task IDs plus revision, hashed), carve validation from scale800 by repository (the heldout dataset is empty), add near-duplicate shingles, and extend config validation to forbidden split use. Config validation already rejects non-train splits in training datasets; extend it to selection stages and call the audit from evaluation and training runs so a hit stops them. Also extend the canary scan to validation and drop the fixed-string limit. Output an audit report that states what it cannot check.

## Acceptance criteria

- Audit fails on a seeded test with an injected overlapping repository, a duplicated instruction, and a canary string.
- Audit passes on the intended splits or lists the hits.
- Report says TermGrade is checked by content hash only.
- Split hash appears in the manifest.
- Every scale800 task maps to a repository, or the report lists the unmapped ones and marks the repository check incomplete.
- The mapping file is reviewed and its hash recorded.

## Test method

Unit tests with synthetic datasets; run on the pinned real revisions (status Verified only after that run).
