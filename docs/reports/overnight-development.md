# Overnight development report, 2026-11-25

Raw logs, traces and Harbor job directories stay on the evaluation host (they are not published). Names in `code` below are file
names there (`logs/`, `runs/`). Per-trial results, trimmed manifests and checks are in [data/](data/); each table names its source.

## 1. Executive summary

- PR #1 (Harbor runner) and PR #2 (prebuilt harness images) are merged.
- Prebuilt images cut trial initialization from 35 to 955 s (or a 1800 s timeout) to 1.5 to 2.4 s.
- Qwen3.8-27B runs on one MI325X with vLLM 0.33.0 ROCm: chat, tool calls, thinking switch and LoRA all work.
- **First real results**: Pi 1.5.2 and OpenCode 2.2.7 each solved a real task end to end, then 12 smoke tasks twice. No
  infrastructure or verifier errors in any of the 122 model trials.
- The Pi adapter loads and is applied by vLLM on ROCm. On the smoke tasks no difference in solve rate was shown.

**The smoke tasks check the pipeline. They are easy, public, written by us and no SWE-bench score.** Numbers are not
protocol-matched with the reference release ([COMPATIBILITY.md](../COMPATIBILITY.md)).

## 2. Pull requests

| PR | Content | Reviewed head | Merge commit | State |
|---|---|---|---|---|
| [#1](https://github.com/tc3oliver/AgentHarnessLab/pull/1) | Harbor runner | `b6bd5be` | `d20e0f0` | merged |
| [#2](https://github.com/tc3oliver/AgentHarnessLab/pull/2) | Prebuilt harness images | `e00c1af` (docs corrected after the last review at `e8fd8ad`) | `879501a` | merged |
| #3 | Findings of the real runs, this report | see the PR | see the PR | see the PR |

Independent review: #1 took three more rounds; two had blocking findings, both fixed (Harbor guesses provider errors by searching the
whole agent output; 0.27.0 skips the verifier after some guesses). #2 had one blocking finding (task images could be stale
relative to a rebuilt harness image), fixed. Reviews were by reading; the test evidence is below.

## 3. Tests

Unit: Ruff, mypy strict, pytest 229 passed (PR #3); 204 at #1, 228 at #2. GitHub Actions on Python 3.12 and 3.13 passed for #1 and #2.

Docker, real Harbor, scripted endpoint (not a model):

| Run | Harbor | Result | Source |
|---|---|---|---|
| #1 at `b6bd5be` | 0.25.0 | oracle 12/12, nop 0/12, Pi passed; OpenCode 1.18.30 setup timeout, passed when repeated | `logs/p0-docker-0.25.0.log`, `logs/p0b-docker-0.25.0.log` |
| #1 at `b6bd5be` | 0.27.0 | oracle 12/12, nop 0/12, Pi 1.5.2 and 1.6.0, OpenCode v2 passed; OpenCode 1.18.30 setup timeout, passed when repeated | `logs/p0-docker-0.27.0.log`, `logs/p0b-docker-0.27.0.log` |
| #2 at `68f665c` | both | oracle, nop and every installed and prebuilt harness case passed; four new 1.19.6 cases failed on both versions because they assumed an exit 1 that prebuilt images do not show | `logs/p1-docker-*.log` |
| #2 at `e00c1af` | both | corrected 1.19.6 cases: 4 of 4 passed on each version | `logs/p1d-docker-*.log` |

The first timeouts happened while the host downloaded 52 GB; the harness install exceeded 1800 s and was recorded as `infra_error`,
as designed. Only the 1.19.6 cases were repeated at `e00c1af`; the other docker cases ran at `68f665c`. Between the two only tests, documentation and a comment
changed. An interim run (`logs/p1c-docker-*.log`) still had one failing 1.19.6 case on 0.27.0.

OpenCode 1.19.6 exit 1: in the interim run 7 of 8 Harbor-installed runs exited 1, all were graded (`solved` or `agent_error`), none was an
infrastructure error, even with "rate limit" or "Invalid API key" in the tool output. 8 of 8 prebuilt runs exited 0.

## 4. Prebuilt images

Initialization is sandbox start plus harness setup (`setup_s`, or Harbor timestamps for #1).

| Harness | Installed per trial | Prebuilt |
|---|---|---|
| Pi (1.5.2, 1.6.0) | 35 to 650 s | 1.5 to 2.1 s |
| OpenCode 1.18.30 | 84 to 99 s, or over 1800 s | 1.8 to 1.9 s |
| OpenCode 2.2.7 | 137 to 955 s | 1.6 to 1.8 s |

Sources: `p0-*`, `p0b-*`, `p1-*` and [data/](data/). The high installed values are from the busy link. The first build of 3 harnesses and 12 tasks took
28 min, including the waiting for that link (`logs/p1-images-build.log`); rebuilding the task images took 94 s (`logs/p1-images-build2.log`).
gitleaks 8.28.0 on three exported harness images: one finding each, a C++ constant in a Node header. It skips some vendored paths, so the
token formats `hf_`, `ghp_` and `npm_` and the endpoint key were also searched for: none found.

## 5. MI325X, ROCm, vLLM

| Item | Value |
|---|---|
| GPU | one MI325X, 0.3 GB in use before start, 0.3 GB after the end; only its render node was passed to the container |
| Container | `vllm/vllm-openai-rocm@sha256:4fcd39b7...fba` (vLLM 0.33.0), no privileged mode, no seccomp or capability change |
| Model | `Qwen/Qwen3.8-27B@37561816e66b`, sha256 of all 19 LFS files verified |
| Load | 50.1 GiB weights, 156 GiB KV cache (2.46 M tokens), engine init 102 s |
| Network | localhost and Docker gateway only, API key required (401 without) |

Checks ([vllm-check.json](data/vllm-check.json)): chat, tool calls 10/10 parsed, follow-up after a tool result, thinking off by default and on when
asked, greedy output stable over 4 calls. No out-of-memory error or traceback in the server logs.
Kernel logs were searched once during the checks with no amdgpu error; the account may not see all kernel messages.
Every agent request in the base runs used temperature 0.8, top-p 1.0 and **top-k 20**, which comes from the model's `generation_config` (`logs/vllm-base.log`).
vLLM reported that it cannot use the ROCm paged-attention kernel for this model and falls back to Triton.
Single-request decode was about 20 to 22 tokens/s, which is slow; not investigated.

## 6. Pi and OpenCode, real tasks

Harbor 0.27.0, Docker 29.6.1, 4 trials at once, prebuilt images. `infra_error` and `verifier_error` were 0 in every run.

Step A ([real-single](data/real-single.jsonl)): `ahl-fix-median`.

| Harness | Outcome | Input / output tokens | Tool calls | Model calls | Agent time | Setup |
|---|---|---|---|---|---|---|
| Pi 1.5.2 | solved | 7,222 / 546 | 3 | 4 | 10.3 s | 1.8 s |
| OpenCode 2.2.7 | solved | 25,447 / 608 | 3 | 4 | 19.1 s | 1.6 s |

Both read the file, edited it, ran their own checks and passed the Harbor verifier.

Step B, 12 tasks, one attempt, run twice:

| Run | Harness | Solved | Failed | Infra | Input / output tokens | Tool calls | Model calls | Sum of agent time |
|---|---|---|---|---|---|---|---|---|
| [real-smoke-1](data/real-smoke-1.jsonl) | Pi | 11 / 12 | 1 | 0 | 219,675 / 12,832 | 64 | 75 | 343 s |
| | OpenCode v2 | 11 / 12 | 1 | 0 | 574,434 / 17,596 | 64 | 75 | 656 s |
| [real-smoke-2](data/real-smoke-2.jsonl) | Pi | 9 / 12 | 3 | 0 | 115,647 / 9,144 | 42 | 53 | 201 s |
| | OpenCode v2 | 10 / 12 | 2 | 0 | 526,609 / 25,227 | 53 | 64 | 934 s |

Peak GPU memory 213 GiB (run 1) and 216 GiB (run 2), mostly preallocated KV cache; mean GPU busy 90% and 95%. Run 2 overlapped with Docker tests on the
CPU, so its times are not comparable. The spread between runs (11 and 9 for Pi) is the noise level: do not rank harnesses from this.
All files in `data/*.manifest.json` carry code commit, image ids, versions and flags. Run 1 and `real-single` used commit `9e13877`, whose tree equals `68f665c` after a rebase.

Token accounting against the vLLM counters: run 1: server 801,593 / 30,504 tokens in 162 requests, results 794,109 / 30,428 in 150 calls. The 12 extra requests match one
uncounted OpenCode title request per trial. For `ab-base` (Pi only) both sides agree exactly: 447,203 / 32,444 in 180 calls.

## 7. Base vs Pi adapter

`harness-hub/Qwen3.8-27B-pi-adapted@41396a9f14d9` (Apache-2.0, weights sha256 verified) with Pi 1.5.2, same server, same flags, 12 tasks x 3 attempts.

Loading check ([lora-ablation.json](data/lora-ablation.json)): mean absolute change of prompt log-probabilities against base: adapter with all `lora_B` zeroed 0.0,
full adapter 0.072, and each of the 7 target modules alone 0.025 to 0.043. So all module types are applied. This does not prove numerical equality with a merged model.

| Run | Solved (3 attempts) | First attempts | Infra | Output tokens | Tool calls | Model calls |
|---|---|---|---|---|---|---|
| [ab-base](data/ab-base.jsonl) | 32 / 36 | 12 / 12 | 0 | 32,444 | 147 | 180 |
| [ab-adapter](data/ab-adapter.jsonl) | 30 / 36 | 9 / 12 | 0 | 31,613 | 103 | 136 |

[Paired comparison](data/ab-compare.md) on first attempts (0 newly solved, 3 lost): p = 0.25. **No difference in solve rate is shown**, and the tasks are near their ceiling.
The adapter used fewer tool calls, the direction its authors report. One host, one server, easy tasks: no claim about the adapter's benchmark results.
The `ab-base` run has `dirty: true`: tests and docs, but no package code, were edited while it ran.

## 8. Problems and open points

Fixed: Harbor's error guessing (#1), stale task images (#2), install time (#2), undeclared top-k and a report that showed pass@1 (first attempts only) beside counts for all attempts, which read as
100% for a 32/36 run (#3).

Open:

- **`ahl-fix-duration-parse` tests more than it states** (`1.5h` must be rejected): 9 of 10 trials failed there, all with that message. Kept as failures ([issue 020](../issues/020-smoke-task-duration-spec.md)).
- OpenCode v1 has not run with a real model; Harbor 0.25.0 has not either.
- Pi's output cap is 16,384 and OpenCode's 32,000 tokens. Compaction was not reached. No 100-step cap for OpenCode.
- Timeout and budget handling were not triggered by the real model; they rest on recorded fixtures.
- Trials cannot be resumed; a broken run starts over. Retries stay off.
- The model revision a server loaded cannot be checked through its API; it is declared.
- A changed image between preflight and run (seconds) would leave the manifest stale; each result's image id stays right.
- OpenCode 2 generated up to 14,034 tokens in one easy task (`real-smoke-2`, `ahl-shell-env-merge`, solved after 557 s).
- Slow decode and the Triton fallback (section 5).

Cleanup: vLLM container removed and GPU memory back to idle, no `ahl-*` container or network left. Model, adapter, logs and images (`agentlab/*`) are kept.
The production stack stayed up throughout. Its LiteLLM gateway is off by design (its README) and was not touched.

## 9. Next task

**One task: serve performance and a larger baseline gate.** Find why decode is about 20 tokens/s (Triton fallback), because it bounds every larger evaluation. Acceptance: measured
single-stream and 16-stream throughput before and after, unchanged greedy outputs, and 36 smoke trials per harness with at most 5% ungraded.
