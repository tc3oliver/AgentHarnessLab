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
| Training | pilot rung 1 (kernel parity) passed; no training run yet |

## Merged pull requests

| PR | What | Merge commit |
|---|---|---|
| #1 | Harbor runner | `d20e0f0` |
| #2 | Prebuilt harness images | `879501a` |
| #3 | Fixes from the first real runs, overnight report | `d7dddbe` |
| #4 | Git and Hugging Face dataset loaders, task-list pins, repository split; smoke task 020 fix | `4d337ee` |

## Log

### 2026-11-26: RL pilot rung 1, kernel parity on gfx942

Image `agentlab-trainer:trl1.19.0` (`rl/trainer-image/Dockerfile`: the vLLM 0.33.0 ROCm image plus
`trl[peft]==1.19.0`, `peft==0.22.0`), GPU 4, no network. Script `rl/parity/kernel_parity.py`, output
`rl/parity/parity-gpu4.jsonl`.

- **Hypothesis:** TRL's tree kernels give correct forward and backward results on MI325X at the model's shapes.
  **Criterion:** relative error at bf16 level (< 1%) against PyTorch fp32 references, deterministic gradients.
  **Met** at 1k, 8k and 32k tokens:
  - causal conv (10240 channels, width 4): forward 0.17%, dx 0.27%;
  - Gated DeltaNet (48 heads, dims 128): forward 0.41%, gradients 0.38-0.48%;
  - identical gradients over 10 repeats;
  - attention backward at head dim 256 finite at 32k tokens (0.25 s, 23 GB peak).
- Risk for the next rung: without `flash-linear-attention`, transformers runs Gated DeltaNet in its PyTorch
  reference implementation, which is slow.

### 2026-11-26: attention backend, paired on devbench

Run `devbench/runs/devbench-r4-aiter`, config `devbench/cfg/devbench-r4-aiter.yaml`. It is round 2 with
`--attention-backend ROCM_AITER_UNIFIED_ATTN`, and nothing else changed. Analysis:
`devbench/analysis/devbench-r4-aiter-vs-default.md`.

- **Hypothesis:** the faster backend does not change task success. **Criterion:** the paired difference CI
  contains 0 for both harnesses. **Met**, and decision 0009 adopts AITER:

  | Harness | Default solved / 90 | AITER | Paired difference (95% CI) | Median agent s |
  |---|---|---|---|---|
  | Pi | 74 | 75 | +1.1 [-7.8, +10.0] | 139 → 54 |
  | OpenCode | 80 | 78 | -2.2 [-11.1, +6.7] | 266 → 115 |

- **OpenCode's round-2 timeouts were not hidden successes.** With AITER, OpenCode had 3 timeouts and 7 wrong
  answers. Round 2 had 10 timeouts and no wrong answers, so the solve rate is the same. The faster model fails the
  same tasks sooner.
- Pi's tool time rose to 47% of agent time, all from four trials with commands that never returned (Pi has no
  command timeout). OpenCode had two runs that ended when the model called the Web Search tool; Harbor recorded one
  as infra. Both behaviours are in COMPATIBILITY.md.

### 2026-11-26: Pi base vs the reference Pi adapter on devbench

Run `devbench/runs/devbench-r3-adapter`, config `devbench/cfg/devbench-r3-adapter.yaml`. It is the same as round 2
(seed, sampling, images, 1800 s budget, attention backend), with served model `pi-adapted` (adapter `41396a9f14d9`)
and Pi only. It is paired against round 2's Pi trials. Analysis: `devbench/analysis/devbench-r3-adapter-vs-base.md`.

| Pi 1.5.2 with | Solved / 90 | Rate (Wilson 95%) | pass@1 | Median agent s | Median tokens in per trial | Mean tool calls (solved) | Tokens per solved |
|---|---|---|---|---|---|---|---|
| base | 74 | 82% (73-89%) | 80% | 139 | 91k | 20.1 | 573k |
| adapter | 80 | 89% (81-94%) | 83% | 72 | 28k | 8.9 | 121k |

- **Hypothesis:** the Pi-specific adapter improves Pi on unseen repositories. **Success criterion:** a paired
  difference whose CI excludes 0. **Not met:**
  - the adapter is better on 6 tasks, the base on 2, and 22 are tied;
  - mean difference +6.7 points, bootstrap 95% CI [-2.2, +15.6], sign test p = 0.29.
- **The efficiency difference is large and consistent:**
  - the adapter makes less than half as many tool calls per solved task;
  - it uses a third of the input tokens per trial;
  - it uses 4.7 times fewer tokens per solved task;
  - it has half the median wall time.

  Failed adapter trials are cheap: 14 turns and 147k input tokens, against 77 turns and 1.73M for the base. The
  adapter gives up or finishes early instead of looping.
- The adapter regresses on `tablib-dbf-export` (0/3, base 2/3) and wins on `markdown-bogus-declaration`,
  `markdown-md-in-html-hr` and `more-itertools-distinct-permutations` (3/3 each, base 1/3).
- With 22 of 30 tasks saturated, devbench cannot resolve a gain of this size. More hard tasks are needed before
  adapter comparisons (Phase B/C) are run on it.

### 2026-11-26: devbench round 2 (30 tasks × 2 harnesses × 3 attempts)

Run `devbench/runs/devbench-r2`, config `devbench/cfg/devbench-r2.yaml` (config hash `bd1edd4e…`), code `6045cb6`
(verifier v4), base model, temperature 0.8, 1800 s per trial, 4 concurrent, default attention backend. Analysis:
`devbench/analysis/devbench-r2.md` (`analysis/analyze.py`).

| Harness | Solved / trials | Rate (Wilson 95%) | pass@1 | Failures | Median agent s | Mean tokens in/out (solved) | Mean tool calls (solved) |
|---|---|---|---|---|---|---|---|
| Pi 1.5.2 | 74 / 90 | 82% (73-89%) | 80% | 14 wrong, 2 timeout | 139 | 195k / 2.2k | 20 |
| OpenCode 2.2.7 | 80 / 90 | 89% (81-94%) | 90% | 10 timeout, 0 wrong | 266 | 630k / 3.8k | 29 |

- Infra, verifier and agent errors: 0 of 180.
- Paired by task: OpenCode is better on 6 tasks, Pi on 2, and 22 are tied. Mean difference +6.7 points, bootstrap
  95% CI [-1.1, +14.4], sign test p = 0.29. **No significant difference between the harnesses.**
- **Every OpenCode failure is a wall-clock timeout**, and on the hardest tasks there were only 30-45 model calls in
  1800 s. OpenCode's prompts are longer (median maximum prompt 24k tokens, against 8k for Pi), and under the
  default attention backend decode slows with context (median request 8.8 tok/s for OpenCode, against 15.8 for
  Pi). The OpenCode failures therefore measure serving speed at least as much as the harness. The backend run
  (Next, item 3) tests this.
- A failed Pi trial costs 8.8 times the input tokens of a solved one (1.72M against 195k) and runs 78 turns on
  average.
- Task tools account for 4% of agent time for both harnesses; the rest is model time.
- 22 tasks are solved in every attempt by both harnesses, so the set is too easy to separate adapters well. Hard
  tasks: `more-itertools-seekable-index` (0/6), `markdown-bogus-declaration` (1/6), `more-itertools-distinct-permutations` (2/6).
- The 4-hour wrapper in `run.sh` would have cut the run off (it took 6 h 46 min). The wrapper process was
  stopped by hand and the evaluation continued unaffected. The limit is now 12 hours.

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

1. More hard tasks: most of the set no longer separates conditions.
2. Harness config fixes before rollouts: a Pi command timeout, and the OpenCode Web Search tool disabled.
3. RL pilot on GPUs 4 and 5:
   - ~~kernel parity~~ (passed);
   - 27B LoRA steps at 16k, 32k and 64k tokens;
   - LoRA hot-load round trip;
   - one OpenEnv Pi rollout;
   - three GRPO steps.
