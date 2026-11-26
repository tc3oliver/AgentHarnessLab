# Research progress log

A running log, newest first. Every result names its run directory (under
`/data3/users/oliver/experiments/agentlab/`, not in git), config and commit. Large logs, checkpoints and weights are
never committed.

## Current state (2026-11-26)

| Area | Status |
|---|---|
| Evaluation | Harbor runner, prebuilt images, Git and Hugging Face dataset loaders (PR #4), devbench (30 tasks), request-level performance monitoring |
| Models served | Qwen3.8-27B `37561816e66b` with the reference Pi adapter `41396a9f14d9` as a LoRA module, vLLM 0.33.0 ROCm, one MI325X |
| Harnesses evaluated with a real model | Pi 1.5.2, OpenCode 2.2.7 (Harbor 0.27.0) |
| Training | not started; pilot plan below |

## Merged pull requests

| PR | What | Merge commit |
|---|---|---|
| #1 | Harbor runner | `d20e0f0` |
| #2 | Prebuilt harness images | `879501a` |
| #3 | Fixes from the first real runs, overnight report | `d7dddbe` |
| #4 | Git and Hugging Face dataset loaders, task-list pins, repository split; smoke task 020 fix | `4d337ee` |

## Log

### 2026-11-26: devbench and the decode slowdown

- **devbench built** (`benchmarks/devbench`, decision 0007): 30 tasks from six MIT/BSD repositories, SWE-smith
  procedural bugs plus hand-written refactorings. Checks before any model run:
  - `check_task.sh` reference solution scores 1 and nop 0 on all 30, with the reference number of passing tests.
  - Harbor 0.27.0 oracle 30/30 and nop 0/30 (`devbench/runs/devbench-oracle`, `devbench-nop`).
  - Repository overlap with scale800, SWE-smith, SWE-bench, SWE-bench Pro and part of SWE-Gym: none.
- **Verifier hardened in three review rounds.** The first version could be passed without a fix:
  - a planted `conftest.py`;
  - in src-layout repositories, a `sitecustomize.py` under `/app/src`. This was confirmed by experiment: it turned
    every fail-to-pass test into a pass.

  - in the jmespath tasks, a module at `/app/unittest.py` shadowing the test runner.

  All three are blocked in verifier v4 (commit `6045cb6`), with adversarial checks. Three round-2 runs started on
  older verifiers were stopped and are archived, not used: `devbench-r2-aborted-verifier-v1`, `-v2` and `-v3`.
- **Round 1** (`devbench/runs/devbench-r1`, first 10 tasks, verifier v1, one attempt):
  - Pi 1.5.2 solved 8/10. Both failures used all 100 turns: `markdown-processing-instruction` and
    `more-itertools-windows-module`.
  - OpenCode 2.2.7 solved 10/10.
  - Infra and verifier errors: 0 of 20.
  - Task tools ran 0-48 s per trial, against 38-1032 s of model time (proxy join, `perf.jsonl`).
- **Decode slowdown explained** (decision 0008, `devbench/perf-attn/results.md`):
  - vLLM's default `ROCM_ATTN` falls back to a Triton paged-decode kernel for this model. Single-request decode is
    69 tok/s at 0.8k tokens of context and 7.6 tok/s at 61k.
  - `ROCM_AITER_UNIFIED_ATTN` gives 78 and 46 tok/s at the same context lengths.
  - A control on a second GPU without LoRA reproduced the slow numbers exactly.
  - The quality effect of switching is not measured yet.
- **RL research** (`rl/rl-research-2026-11-26.md`). TRL 1.19.0 (2026-11-25):
  - `AsyncGRPOTrainer` is stable.
  - It accepts vLLM < 0.35.
  - LoRA syncs to vLLM through `/v1/load_lora_adapter`.

  OpenEnv 0.14.0 validates Pi and OpenCode v1 rollouts; its Harbor extra still resolves Harbor 0.25.0 (fastmcp
  conflict). Untested on gfx942: TRL's tree Gated DeltaNet and conv kernels, and the attention backward at head
  dim 256.

### 2026-11-25: first real runs

See [overnight-development.md](overnight-development.md): smoke tasks 11/12 for both harnesses, prebuilt images,
base vs adapter on smoke (no difference shown).

## Next

1. Round 2: devbench 30 tasks × Pi and OpenCode × 3 attempts (`devbench-r2`, verifier v4, started 03:18 UTC; running).
2. Pi base vs the reference Pi adapter on devbench, paired, 3 attempts.
3. Attention backend: the same tasks with `ROCM_AITER_UNIFIED_ATTN`, paired against round 2. Decides the rollout
   backend.
4. RL pilot on GPUs 4 and 5:
   - kernel parity (`rl/parity/kernel_parity.py`);
   - 27B LoRA steps at 16k, 32k and 64k tokens;
   - LoRA hot-load round trip;
   - one OpenEnv Pi rollout;
   - three GRPO steps.
