# 0007: A generated development benchmark instead of more smoke tasks

Status: accepted. Date: 2026-11-26.

## Context

The 12 smoke tasks were solved in 11 of 12 trials by Qwen3.8-27B, so they cannot separate harnesses or adapters.
SWE-bench Pro is the test set and is evaluated once per final configuration; scale800 and TermGrade have unclear
licences. Development decisions (serving settings, harness configuration, adapter selection) need a set that is
harder than smoke, legally clear, cheap to run and allowed to be looked at repeatedly.

## Decision

Build `benchmarks/devbench`: Harbor tasks from permissively licensed Python repositories pinned by commit and
archive checksum, with SWE-smith's procedural modifiers used as a library to create bugs and hand-written tasks for
refactoring. Every task is rebuilt deterministically from `tasks.yaml`; the verifier restores pristine upstream
tests at verification time; oracle must score 1 and nop 0. Repositories already used by scale800, SWE-smith,
SWE-bench, SWE-bench Pro or SWE-Gym are excluded. The set is a validation split: it may be used for selection, and
results on it are never reported as a benchmark score.

## Consequences

- Cheap to extend: a new task is a few lines in `tasks.yaml` plus an instruction.
- Procedural bugs are local and often easy; the set needs harder tasks (multi-bug, feature work, larger
  repositories) to stay discriminative. Difficulty must be measured, not assumed.
- The libraries are in the model's pretraining data; the benchmark measures fixing synthetic bugs in familiar code,
  not unseen code.
