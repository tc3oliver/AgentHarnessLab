# devbench report: Pi 1.5.2 and OpenCode 2.2.7 on Qwen3.8-27B

Date: 2026-11-26. devbench is a **development benchmark** for decisions inside this project (decision
[0007](../DECISIONS/0007-development-benchmark.md)). It is not SWE-bench and not a held-out test set, and its
numbers must not be reported as either. Run directories are under `/data3/users/oliver/experiments/agentlab/devbench/`,
outside git. Trial-level results (`results.jsonl`), manifests, Harbor logs and the request log are there; analysis
tables are in `analysis/` (script `analysis/analyze.py`).

## Summary

- **Pi and OpenCode (base model), side by side** (the protocol does not rank harnesses, see Paired comparisons): Pi solved 74/90 (82%), OpenCode 80/90 (89%). Paired by task the difference is
  not significant (+6.7 points for OpenCode, 95% CI [-1.1, +14.4], sign test p = 0.29). OpenCode uses about 3
  times the input tokens and twice the wall time.
- **Reference Pi adapter vs base, under Pi:** 80/90 against 74/90, not significant (+6.7 points, CI [-2.2,
  +15.6], p = 0.29). The adapter is much cheaper: 4.7 times fewer tokens per solved task and half the tool calls,
  and its failures end early instead of looping.
- **Attention backend:** `ROCM_AITER_UNIFIED_ATTN` cuts median trial time by about 2.4 times (wall time of a full run by 1.55 times) with no significant
  difference in success, and is now the default (decision [0009](../DECISIONS/0009-aiter-attention-backend.md)).
- **Reliability:** 0 infra or verifier errors in 270 trials on the default backend. On AITER there were 2 OpenCode
  runs that ended when the model called the Web Search tool (one recorded by Harbor as infra), see Limits.
- **The benchmark is saturated:** 19-25 of 30 tasks are solved in every attempt under each condition, 15 under all
  five conditions. It cannot resolve differences of about 7 points. More hard tasks are needed before it decides between adapters.

## Sources and licences

Six Python repositories at pinned commits, each licence checked in the repository at that commit:
Python-Markdown (BSD-3-Clause), tablib (MIT), more-itertools (MIT), jmespath.py (MIT), python-semver
(BSD-3-Clause) and itsdangerous (BSD-3-Clause). Bugs come from SWE-smith's procedural modifiers
(`SWE-bench/SWE-smith@9b74ac08`, MIT) used as a library; refactoring tasks are hand-written. Source is fetched
from GitHub archives with checked sha256 when an image is built, not stored in this repository. Full table,
construction and verifier: [benchmarks/devbench/README.md](../../benchmarks/devbench/README.md).

| Category | Tasks | What the agent gets |
|---|---|---|
| bug-fix | 7 | issue-style description; failing tests hidden |
| multi-file | 6 | two or three bugs in different modules |
| navigation | 6 | user report with a reproduction, no file names |
| refactoring | 4 | a structural change checked by hidden tests |
| test-repair | 7 | "the suite fails, fix the code"; failing tests visible |

Checks before model runs:
- oracle 30/30 and nop 0/30, under `check_task.sh` and under Harbor;
- no repository overlap with scale800, SWE-smith's Python profiles, SWE-bench, SWE-bench Pro, or the part of
  SWE-Gym that could be listed;
- no shared content with the smoke tasks in `agentlab audit`.

## Protocol

| Item | Value |
|---|---|
| Model | `Qwen/Qwen3.8-27B@37561816e66b`; adapter `harness-hub/Qwen3.8-27B-pi-adapted@41396a9f14d9` (LoRA module `pi-adapted`) |
| Serving | vLLM 0.33.0 ROCm (`vllm/vllm-openai-rocm@sha256:4fcd39b7…`), one MI325X (GPU 5), bf16, max length 131072, prefix caching, LoRA enabled in every run |
| Sampling | temperature 0.8, top_p 1.0, top_k 20, thinking off |
| Harnesses | Pi 1.5.2 (100 turns), OpenCode 2.2.7 (`opencode-v2`), prebuilt harness images |
| Runner | Harbor 0.27.0, 4 trials at a time, 1800 s per trial, seed 0, 3 attempts per task |
| Verifier | v4 (commit `6045cb6`): pristine tests restored, isolated interpreter, shadow-module check, `min_passed` |
| Monitoring | pass-through proxy logging every request's timing and tokens, joined to trials by container IP; engine and GPU sampler |
| Isolation | no other Docker or GPU work on the host's test GPUs during runs; production GPUs 0-3 untouched |

| Run | Condition | Config hash | Code | Wall time |
|---|---|---|---|---|
| `devbench-r2` | Pi and OpenCode, base, default `ROCM_ATTN` | `bd1edd4e…` | `6045cb6` (manifest `dirty`: the untracked progress log, committed as `84de983`) | 6 h 46 min |
| `devbench-r3-adapter` | Pi, adapter, default backend | `3b0d3c70…` | `84de983` | 2 h 00 min |
| `devbench-r4-aiter` | Pi and OpenCode, base, `ROCM_AITER_UNIFIED_ATTN` | `e38f029f…` | `548fb12` | 4 h 22 min |

Later code commits changed documentation only, so tasks, verifier and runner are identical across the three runs
(same dataset hash `sha256:fffb77f8…`). Paired comparisons are by task: per-task solve rate over 3 attempts,
sign test over tasks that differ, and a bootstrap CI over tasks. Earlier round-1 and aborted round-2 runs (older
verifiers) are not used here.

## Results

### Per harness and condition

| Condition | Solved / 90 | Rate (Wilson 95%) | Failures (of which timeout) | Median agent s | Median input / output tokens per trial | Mean tool calls, solved | Mean input tokens, solved / failed | Tokens per solved task |
|---|---|---|---|---|---|---|---|---|
| Pi, base | 74 | 82% (73-89%) | 16 (2) | 139 | 91k / 2.0k | 20.1 | 195k / 1.73M | 573k |
| Pi, adapter | 80 | 89% (81-94%) | 10 (2) | 72 | 28k / 1.3k | 8.9 | 99k / 147k | 121k |
| Pi, base, AITER | 75 | 83% (74-90%) | 15 (4) | 54 | 100k / 1.9k | 21.9 | 214k / 1.20M | 459k |
| OpenCode, base | 80 | 89% (81-94%) | 10 (10) | 266 | 318k / 2.5k | 28.6 | 630k / 3.10M | 1.02M |
| OpenCode, base, AITER | 78 | 87% (78-92%) | 11 (3), plus 1 recorded as infra | 115 | 233k / 2.2k | 27.4 | 599k / 5.92M | 1.46M |

Tokens per solved task = all input and output tokens of the condition divided by solved trials, so it includes the
cost of failures. No price is attached: the model is self-hosted.

### Paired comparisons

| Comparison | Tasks better (A / B / tied) | Mean difference A - B | 95% bootstrap CI | Sign test p |
|---|---|---|---|---|
| OpenCode vs Pi (base, default backend) | 6 / 2 / 22 | +6.7 points | [-1.1, +14.4] | 0.29 |
| Pi adapter vs Pi base | 6 / 2 / 22 | +6.7 | [-2.2, +15.6] | 0.29 |
| Pi: AITER vs default | 5 / 6 / 19 | +1.1 | [-7.8, +10.0] | 1.00 |
| OpenCode: AITER vs default | 3 / 4 / 23 | -2.2 | [-11.1, +6.7] | 1.00 |

Harness comparisons are of harness and model together; harnesses differ in prompts, context handling and tools,
so the OpenCode-Pi difference is not a statement about either harness alone.

### Per task (solved / 3 attempts)

| Task | Category | Pi base | Pi adapter | Pi base, AITER | OpenCode | OpenCode, AITER |
|---|---|---|---|---|---|---|
| `markdown-footnote-backrefs` | bug-fix | 2/3 | 3/3 | 2/3 | 3/3 | 3/3 |
| `more-itertools-collapse-levels` | bug-fix | 3/3 | 3/3 | 3/3 | 2/3 | 3/3 |
| `more-itertools-distinct-permutations` | bug-fix | 1/3 | 3/3 | 3/3 | 1/3 | 1/3 |
| `more-itertools-gray-product` | bug-fix | 1/3 | 1/3 | 1/3 | 3/3 | 3/3 |
| `more-itertools-seekable-index` | bug-fix | 0/3 | 0/3 | 1/3 | 0/3 | 1/3 |
| `tablib-ods-dates` | bug-fix | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `tablib-sql-commit` | bug-fix | 3/3 | 2/3 | 2/3 | 3/3 | 1/3 |
| `jmespath-error-messages` | multi-file | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `markdown-bogus-declaration` | multi-file | 1/3 | 3/3 | 2/3 | 0/3 | 2/3 |
| `more-itertools-primes` | multi-file | 2/3 | 3/3 | 1/3 | 3/3 | 3/3 |
| `semver-match-and-cli` | multi-file | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `tablib-dbf-export` | multi-file | 2/3 | 0/3 | 1/3 | 3/3 | 1/3 |
| `tablib-ragged-import` | multi-file | 3/3 | 3/3 | 2/3 | 3/3 | 3/3 |
| `jmespath-function-types` | navigation | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `markdown-attr-list-class` | navigation | 3/3 | 3/3 | 2/3 | 3/3 | 3/3 |
| `markdown-legacy-attrs` | navigation | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `markdown-md-in-html-hr` | navigation | 1/3 | 3/3 | 3/3 | 3/3 | 2/3 |
| `markdown-processing-instruction` | navigation | 2/3 | 2/3 | 2/3 | 2/3 | 1/3 |
| `markdown-wikilinks-meta` | navigation | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `jmespath-comparisons-module` | refactoring | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `markdown-registry-module` | refactoring | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `more-itertools-windows-module` | refactoring | 2/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `tablib-row-module` | refactoring | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `itsdangerous-failing-suite` | test-repair | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `jmespath-failing-suite` | test-repair | 3/3 | 3/3 | 2/3 | 3/3 | 3/3 |
| `more-itertools-running-max` | test-repair | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `more-itertools-running-mean` | test-repair | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `semver-failing-suite` | test-repair | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `tablib-failing-suite` | test-repair | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| `tablib-latex-suite` | test-repair | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

| Category | Tasks | Pi base | Pi adapter | Pi base, AITER | OpenCode | OpenCode, AITER |
|---|---|---|---|---|---|---|
| bug-fix | 7 | 13/21 | 15/21 | 15/21 | 15/21 | 15/21 |
| multi-file | 6 | 14/18 | 15/18 | 12/18 | 15/18 | 15/18 |
| navigation | 6 | 15/18 | 17/18 | 16/18 | 17/18 | 15/18 |
| refactoring | 4 | 11/12 | 12/12 | 12/12 | 12/12 | 12/12 |
| test-repair | 7 | 21/21 | 21/21 | 20/21 | 21/21 | 21/21 |

Hard under every condition: `more-itertools-seekable-index` (2 of 15 trials) and `markdown-processing-instruction`
(9/15). Hard for Pi only: `more-itertools-gray-product` (3 of 9 Pi trials; OpenCode 6/6). `tablib-dbf-export` is solved by OpenCode and missed by the adapter
(0/3), the one clear adapter regression.

### Where the time goes

From the proxy join (`perf.jsonl`): model time is the union of a trial's request intervals; harness time is the
rest of agent time (tools, harness overhead).

| Condition | Model s (sum) | Harness and tool s (sum) | Tool share | Median of max prompt tokens per trial | Median decode tok/s per request (>= 32 output tokens) |
|---|---|---|---|---|---|
| Pi, base | 26,713 | 1,087 | 3.9% | 8.4k | 15.8 |
| Pi, adapter | 23,067 | 592 | 2.5% | 6.2k | 20.9 |
| Pi, base, AITER | 8,863 | 7,954 | 47% | 8.7k | 52.8 |
| OpenCode, base | 56,343 | 2,408 | 4.1% | 23.7k | 8.8 |
| OpenCode, base, AITER | 27,336 | 1,507 | 5.2% | 21.4k | 20.9 |

On the default backend almost all agent time is model time. The 47% for Pi on AITER comes from five trials whose shell
commands never returned (one `find /`, others looping test scripts) and used up 786-1777 s each; Pi has no command
timeout. Without them Pi's tool share on AITER is 11%.

## Performance

The earlier observation of decode dropping from about 43 to 18 tok/s in long trials is explained by the attention
backend, not by the harness, LoRA or tool latency ([COMPATIBILITY.md](../COMPATIBILITY.md#serving-attention-backend-and-long-context-decode-vllm-0330-rocm-qwen38-27b)):

- vLLM 0.33.0 picks `ROCM_ATTN` for this model. Its custom kernel needs head size 64 or 128 (the model's full
  attention uses 256), so decode falls back to a Triton paged kernel that slows in proportion to context:
  69 tok/s at 0.8k prompt tokens, 7.6 at 61k, single request.
- `ROCM_AITER_UNIFIED_ATTN` gives 78 and 46 tok/s at the same lengths. A control on a second GPU without LoRA
  reproduced the default backend's numbers.
- Under load (4 concurrent agents) the median request decodes at 8.8 tok/s for OpenCode, whose contexts are longer,
  and 15.8 for Pi. AITER raises these to 20.9 and 52.8.
- No vLLM kernel or optimisation setting was changed beyond selecting an existing backend, and that only after the
  paired quality check.

## Limits

- **Contamination:** all six libraries are popular and certainly in the base model's pretraining data; the bugs
  are synthetic but the code around them is not new. Repository overlap was checked against the datasets listed
  above only; SWE-rebench, R2E-Gym and other mined datasets were not checked, and nothing measures memorisation.
- **Saturation and size:** 30 tasks from six repositories, three attempts. 19-25 tasks are always solved under a
  given condition (15 under all five), so effective sample size is the 5-11 tasks that vary. Differences under about 15 points are not resolvable.
- **Bias:** single language (Python), libraries only, mostly local procedural bugs; three of the six repositories
  supply 23 of the 30 tasks. Instructions were written by one person from the failing tests. The adapter was trained for Pi
  on another task distribution; this set says nothing about other harnesses' adapters.
- **Budget binds differently:** a wall-clock budget makes slow serving look like harness failure. On the default
  backend all 10 OpenCode failures were timeouts; on AITER the failures were mostly on the same tasks
  but mostly wrong answers, and three tasks OpenCode had always solved (`tablib-dbf-export`, `tablib-sql-commit`,
  `markdown-md-in-html-hr`) failed at least once.
- **Verifier gaps:** it does not restore `pyproject.toml`, `setup.cfg` or `tox.ini` and does not detect edits to
  installed packages. Three earlier gaps were found in review and closed (planted `conftest.py`, `sitecustomize.py`,
  a module shadowing `unittest`).
- **Compatibility:** Pi has no command timeout. OpenCode 2.2.7 offers a Web Search tool that ends non-interactive runs.
  Harbor 0.27.0 misclassified one such end as `ApiRateLimitError` and passes the endpoint API key on the
  `docker compose` command line (visible to `ps` on a shared host). Details in
  [COMPATIBILITY.md](../COMPATIBILITY.md#harness-behaviour-seen-on-devbench-pi-152-opencode-227-harbor-0270).

## Is RL training ready?

**Evaluation side: ready for a pilot, not for adapter comparisons.** The pipeline is reliable (0 infra errors in 270
default-backend trials), every trial is traceable to a run, config, commit and request log, and the faster backend
is validated. Before GRPO is used to compare methods (Phase B/C):

1. devbench needs harder tasks, or comparisons must use a larger validation split carved from the training
   distribution by repository;
2. Pi needs a command timeout and OpenCode's Web Search tool must be off, so rollouts do not waste their budget;
3. the training side has to pass the pilot ladder on ROCm (`RESEARCH_PROGRESS.md`, Next). The first rung has
   passed: TRL 1.19.0's tree Gated DeltaNet and causal-conv kernels match PyTorch references at 1k, 8k and 32k
   tokens with Qwen3.8-27B's shapes (relative error 0.2-0.5% in bf16 against fp32, forward and all input
   gradients, deterministic over 10 repeats), and attention backward at head dim 256 runs at 32k tokens
   (`rl/parity/parity-gpu4.jsonl`, image `agentlab-trainer:trl1.19.0`). Still open: LoRA steps at long context
   (transformers falls back to a slow PyTorch Gated DeltaNet when `flash-linear-attention` is missing), LoRA
   hot-load, one OpenEnv rollout, three GRPO steps.

Until those pass, no large GPU allocation for GRPO.
