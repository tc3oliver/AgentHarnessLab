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
| Training | pilot rungs 1-5 passed (kernel parity, 27B LoRA steps to 64k on one GPU, LoRA hot-load into vLLM, OpenEnv Pi rollout with token capture, three async GRPO steps); no training run that is meant to improve the model yet |

## Merged pull requests

| PR | What | Merge commit |
|---|---|---|
| #1 | Harbor runner | `d20e0f0` |
| #2 | Prebuilt harness images | `879501a` |
| #3 | Fixes from the first real runs, overnight report | `d7dddbe` |
| #4 | Git and Hugging Face dataset loaders, task-list pins, repository split; smoke task 020 fix | `4d337ee` |
| #5 | devbench, request monitoring, verifier v4, benchmark report, ADR 0009 | `d764ce6` |
| #6 | Rollout harness configs (ADR 0010), proxy path allowlist, LoRA serving options | `a2b51a5` |

## Log

### 2026-11-26: Flash-Next feasibility probes (Phase D)

Full note: [flash-next-feasibility.md](flash-next-feasibility.md). GPU 6, artifacts in `flashnext/`.
- **Serving with LoRA:** works on one GPU, but only with the Triton FP8 MoE backend. With LoRA on, vLLM refuses the
  AITER MoE backend at startup.
  - An identity adapter matches the base model exactly (Δ logprob 0.0).
  - A random adapter changes the output, so the adapter is really applied.
  - Decode speed: 114 tok/s base, 73 tok/s with the adapter (one request).
- **Training step:** blocked. The FP8 checkpoint loads in the trainer image (169 GB on one GPU). The forward pass
  fails, because transformers' fine-grained FP8 kernel comes from the `kernels` Hub loader, which we do not install
  (same policy as pilot rung 2).
- **Recommendation:** v0.5 stays evaluation-only until a reviewed, vendored FP8 kernel exists.

### 2026-11-26: devbench hard tier (10 tasks), built, not yet evaluated

The original 30 tasks saturate. Test-repair and refactoring were solved in 124/126 and 59/60 trials across all five
conditions (`devbench/analysis/combined.md`). The hard tier adds 10 tasks (`configs/datasets/devbench-hard.yaml`):
5 bug-fix tasks with one single-hunk patch and 1 hidden fail-to-pass test each, and 5 multi-file tasks with 3
patches in 3 files each. They cover 5 repositories, 2 tasks each.
- **Selection by construction only.** No model was run on candidates. The rules were fixed first, applied to the
  validated SWE-smith pool, and the list was frozen. Only oracle and nop checks could exclude a task. Choosing by
  model failure would bias later base-vs-adapter comparisons. The rules are in `benchmarks/devbench/README.md`.
- **Checks:** oracle 10/10 and nop 0/10 (`check_task.sh`). The rebuild of all 40 tasks is deterministic.
  `devbench.yaml` now lists its 30 tasks with the unchanged hash, so earlier results stay comparable.
- **Review** found one rule violation, which was fixed: a patch in a function already used by an original task.
  It also found instructions that named internal modules. These now name only the public API.

### 2026-11-26: RL pilot rung 5, three async GRPO steps through OpenEnv

TRL 1.19.0 `HarnessAsyncGRPOTrainer` (image `agentlab-trainer:trl1.19.0-openenv0.14.0`) on GPU 4 with Qwen3.8-27B
plus a fresh LoRA. Rollouts come from vLLM on GPU 5 through OpenEnv 0.14.0 (Pi harness, Docker sandbox, capture proxy
on the Docker bridge as in rung 4). Script and log: `rl/grpo-pilot/` (`grpo_pilot.py`, `run.sh`, `pilot.log`).
Adapters and `log_history.json`: `rl/adapters/grpo-pilot/`. OpenEnv server log: `rl/openenv/serve.log`.

- **Hypothesis:** the stack completes GRPO steps end to end. This rung tests plumbing, not learning.
- **Data:** this repository's 12 smoke tasks (Apache-2.0), as in rung 4.
- **Settings:**
  - 4 generations per task, 3 steps, lr 1e-6, temperature 1.0, `max_staleness` 1;
  - LoRA r 32, alpha 64, on `q,k,v,o,gate,up,down`;
  - `agent_timeout_sec` 600, 30 agent steps, 90-minute wall limit (not enforced, see below).
- **Reward:** the verifier's 0/1 plus 0.3 × clip(1 − tool calls / 15, 0, 1) when solved. Without the bonus, every
  group of 4 on the smoke tasks scored the same and gave no advantage. Rewards above 1 come from this bonus.
- **Criteria:** three optimiser steps, each followed by an adapter sync that vLLM serves (`trl-policy-v1..v3`),
  token capture on every rollout, finite loss, no crash. **Met.**

| Step | Loss | Grad norm | Reward (rollout mean) | Group std | IS ratio min / mean / max | Clip region | Sync |
|---|---|---|---|---|---|---|---|
| 1 | −0.111 | 0.069 | 1.110 | 0.167 | 0.27 / 1.000 / 2.82 | 0.10 % | 1.02 s |
| 2 | −0.128 | 0.073 | 1.152 | 0.155 | 0.48 / 1.000 / 4.47 | 0.11 % | 0.97 s |
| 3 | −0.130 | 0.053 | 1.099 | 0.164 | 0.29 / 1.000 / 1.62 | 0.09 % | 1.12 s |

- 51–68 trained samples per step (about 92k–98k trained tokens out of 127k–131k forwarded), 25–26 minutes per
  step for steps 2 and 3, 105 minutes of training time in total (`train_runtime`).
- Rollout drift tokens were 0 in all three logged steps. Staleness was at most 1. The final summary row of
  `log_history.json` (drift max 261, mean 0.96) also counts the rollouts cancelled at shutdown.
- The OpenEnv server probed each adapter (v1, v2, v3) as `capture_level=tokens rollout_type=train`.
- 4 rollouts failed with `rollout produced no capture`. All 4 came after `Stopping AsyncRolloutWorker`: they were
  in flight when training ended and were cancelled. None failed during the three steps.
- The rewards do not show learning, and three steps at lr 1e-6 are not expected to. Most of the signal is the
  tool-call bonus. Mean group std is 0.16, because the smoke tasks are nearly always solved. A real run needs a
  training set with a licence cleared for training and a solve rate well below 1.
- **Workarounds** (in `grpo_pilot.py`, none in TRL or OpenEnv):
  - TRL's async trainer calls the vLLM dev routes `/server_info`, `/pause` and `/resume`. vLLM serves those only
    in dev mode, unauthenticated, so dev mode stays off. The pilot returns a fixed server info and makes
    pause/resume no-ops. That is safe here only because LoRA sync is a hot-load, not an in-place weight write.
  - Tree attention uses the image's own `flash_attn` 2.8.3 instead of the Hub kernel (rung 2).
  - The LoRA targets name the language-model projections explicitly. `all-linear` also matches the vision tower,
    whose modules vLLM rejects.
- **Wall limit not enforced:** `timeout 5400 docker run ...` killed only the Docker client at 90 minutes, and the
  container trained on past the 90-minute limit, to 105 minutes of training time. This is the same mistake as the round 2 wrapper. `run.sh` now runs
  `timeout` inside the container (`--init`, entrypoint `timeout -s TERM -k 60 $LIMIT python3 ...`, checked: exit
  124 on a 2 s limit). A host watchdog also runs `docker stop` LIMIT + 300 s after launch. Every later training
  or eval container needs its limit enforced the same way.
- **OpenEnv quirk:** a session's `api_key` overrides the server's own. TRL's factory passes an empty one by
  default, so the capability probe got a 401. The server then cached the endpoint as `capture_level=text`
  (evaluation only), and every rollout came back untrainable. Passing the key fixes the probe. The cache lasts as
  long as the server, so the server has to be restarted after a failed probe.

### 2026-11-26: RL pilot rung 4, one OpenEnv Pi rollout with token capture

OpenEnv 0.14.0 (resolves Harbor 0.25.0) in its own venv, Docker sandbox, vLLM on GPU 5 with
`--return-tokens-as-token-ids --logprobs-mode processed_logprobs` (AITER backend). Data: this repository's smoke
task `ahl-csv-aggregate` (Apache-2.0). Training sources (scale800, termgrade) stay blocked on their licence
questions (DATASETS.md), and devbench is never trained on. Output `rl/openenv/rollout-pi-0.json`.

- **Criterion:** a graded rollout that is trainable (`rollout_type: train`, token ids and log-probs on every turn).
  **Met:**
  - reward 1.0, 4 turns, 72 s, capture level `tokens`;
  - 897 trainable tokens, each turn with prompt and completion token ids, per-token log-probs and a loss mask;
  - the ATIF trajectory check matches.
- **Security fix needed for a shared host:** OpenEnv's capture proxy binds `0.0.0.0` (hard-coded in
  `CaptureServer.start`), and `--expose direct` advertises `127.0.0.1`, which a Docker sandbox cannot reach.
  `rl/openenv/rollout_bridge.py` wraps the CLI. It binds the proxy and advertises it on the Docker bridge gateway
  (172.17.0.1), reachable from local containers but not from other machines, and refuses any expose mode other
  than `direct`, since `gradio` (the default) and `cloudflare` open public tunnels. OpenEnv itself is unmodified.
  OpenEnv keeps the real endpoint key in its own process; the agent gets a per-rollout session id instead.

### 2026-11-26: RL pilot rung 3, LoRA hot-load round trip, trainer to vLLM

Trainer on GPU 4 (`rl/parity/lora_roundtrip.py`), vLLM on GPU 5 (AITER backend, `scripts/serve_vllm_rocm.sh` with
the new `LORA_DIR`, which enables `/v1/load_lora_adapter`), sampling script `rl/parity/rt_vllm.py`. Adapters are in
`rl/adapters/rt-step{1,2}`, not in git.

- **Hypothesis:** an adapter saved by the trainer (PEFT, r 32, all linear) can be hot-loaded and replaced by name in
  vLLM, and vLLM's log-probs of its own samples match the trainer's.
- **Criteria:** the replacement takes effect immediately, and the mean absolute log-prob difference is < 0.05.
  **Met:**
  - Two adapters were trained to visibly different behaviour: one on code with "The answer to everything is 42",
    the other on "The capital of France is Berlin".
  - After `unload` and `load` under the same name, vLLM's completions switched at once, from "Paris" to "Berlin".
    The prompts were 5-7 tokens, shorter than a cache block, so a stale prefix cache after a same-name swap is not
    excluded. TRL avoids the question by loading every version under a new name.
  - On 4 prompts × 48 sampled tokens at temperature 1, the trainer's log-probs (TRL tree-attention path) against
    vLLM's:

    | Adapter | Mean abs diff | Max abs diff | Importance ratio range |
    |---|---|---|---|
    | step 1 | 0.007 | 0.20 | 0.82-1.10 |
    | step 2 | 0.012 | 0.20 | 0.82-1.14 |
- The first attempt trained both adapters on the same text, so they were indistinguishable on the sampled tokens
  and could not show that the swap took effect. The second adapter was retrained on different text.
- The trainer forward needs `use_cache=False` on the tree path (otherwise transformers' recurrent cache update
  fails).

### 2026-11-26: RL pilot rung 2, local FlashAttention and 27B LoRA steps up to 64k tokens

GPU 4, image `agentlab-trainer:trl1.19.0`, no network. Scripts and outputs are in `rl/parity/`.

- **Attention kernel:** TRL 1.19.0's tree attention fetches `kernels-community/aiter-flash-attn` from the Hub at
  run time, but the image has no `kernels` package. We use the image's own ROCm `flash_attn` 2.8.3 instead, with no
  binary downloaded at run time. `fa_parity.py` (`fa-gpu4.jsonl`), varlen, causal, 24 query and 4 KV heads, head
  dim 256, against fp32 SDPA:
  - output 0.20-0.21%, dq 0.27-0.28%, dk 0.33%, dv 0.32% at 1k, 8k and 16k tokens;
  - 64k forward and backward finite in 0.78 s.
- **LoRA steps** (`lora_step.py`, `lora-gpu4-v2.jsonl`):
  - setup: Qwen3.8-27B in bf16, LoRA r 32 on all linear layers (233M trainable), gradient checkpointing, TRL tree
    attention and tree Gated DeltaNet and conv, chunked loss, AdamW;
  - **criterion:** one finite forward, backward and optimizer step at 64k tokens on one GPU. **Met**, on random
    tokens in a single tree segment: this shows memory and numerics, not multi-branch tree packing.

  | Tokens | Step s | Peak GB |
  |---|---|---|
  | 4k (first step, includes warm-up) | 46 | 65 |
  | 16k | 16 | 75 |
  | 32k | 26 | 93 |
  | 64k | 52 | 132 |

  Loss on random tokens is 12.4, about ln(vocabulary size), as expected.
- **First attempt failed:** out of memory at 16k tokens, 182 GB at 4k. The test left the model in eval mode, so
  gradient checkpointing was off, and it built full-vocabulary fp32 logits. Both are fixed in the script.
  TRL's trainer scores only sampled tokens.

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
  answers. Round 2 had 10 timeouts and no wrong answers, so the solve rate is the same. The faster model fails
  mostly the same tasks sooner, plus a few single failures on tasks it had always solved.
- Pi's tool time rose to 47% of agent time, all from five trials with commands that never returned (Pi has no
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
- With 19 tasks solved 3/3 under both conditions, devbench cannot resolve a gain of this size. More hard tasks are needed before
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
- A failed Pi trial costs 8.8 times the input tokens of a solved one (1.73M against 195k) and makes 77 model calls
  on average.
- Task tools account for 4% of agent time for both harnesses; the rest is model time.
- 19 tasks are solved in every attempt by both harnesses, so the set is too easy to separate adapters well. Hard
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

1. ~~More hard tasks~~ (10-task hard tier built); evaluate it: Pi vs OpenCode and Pi base vs adapter, 3 attempts each.
2. Harness configs for rollouts (decision 0010): OpenCode web tools denied (`opencode-v2-noweb.yaml`); Pi unmodified.
3. RL pilot on GPUs 4 and 5:
   - ~~kernel parity~~ (passed);
   - ~~27B LoRA steps at 16k, 32k and 64k tokens~~ (passed, 132 GB at 64k);
   - ~~LoRA hot-load round trip~~ (passed);
   - ~~one OpenEnv Pi rollout~~ (passed; capture proxy bound to the Docker bridge);
   - ~~three GRPO steps~~ (passed; plumbing only, no learning signal on the smoke tasks).
4. A training set with a licence cleared for training and a solve rate well below 1. Scale800 and termgrade are
   still blocked on their licence questions (DATASETS.md).
