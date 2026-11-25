# Experiments

Research design is in [RESEARCH.md](RESEARCH.md); data rules in [DATASETS.md](DATASETS.md); upstream facts in [UPSTREAM.md](UPSTREAM.md). Status: the mock runner, result and manifest schemas, config validation, metrics, paired comparison and Markdown reports exist in `src/`; Harbor smoke tasks (oracle, nop) exist. No model-backed run has happened. Everything below about real runs is **Planned** unless it says it is implemented.

## Evaluation protocol

1. An experiment config names: model (Hub ID + revision), optional adapter (path or revision), dataset (ID + revision; a split-file hash is Planned), harness (`pi` or `opencode`) and its version, inference parameters, seed, attempts per task (`n_attempts`), per-trial limits. The Harbor version is recorded in the environment lock (issue 002), not yet in the config.
2. Each (task, harness, sample index) is one Harbor trial. The Harbor-backed runner (Planned, issue 001) starts a job from the config and parses each `TrialResult` into the project result schema. Only the mock runner exists today.
3. Evaluation uses the same harness, tool set and version as training for that arm. Pi and OpenCode are never compared with each other on pass@1 (they differ in context compaction); only within a harness.
4. The serving endpoint is a vLLM OpenAI-compatible server. Pi needs `model_api=openai-completions` and an environment-variable name for the key ([UPSTREAM.md](UPSTREAM.md#reusable-pieces)).
5. For adapters, vLLM serves the base model with the adapter loaded; the adapter is identified in the manifest by file hash (Planned).
6. Test sets are run once per final configuration.

## Harbor status to outcome rules

Each trial maps to exactly one outcome. The outcome names and the rule that `infra_error` leaves every denominator are implemented (`core/results.py`, `evaluation/metrics.py`). The mapping from Harbor `TrialResult` fields (`verifier_result`, `exception_info`, `reward_valid`) to these outcomes is **Planned** (issue 001) and **Unverified** against real trials.

| Trial situation | Outcome | In pass@1 denominator | Reported |
|---|---|---|---|
| Verifier ran, reward = 1 (pass threshold fixed in config) | `solved` | yes | yes |
| Verifier ran, reward below threshold | `failed` | yes | yes |
| Agent timeout | `timeout` | yes | yes, separate count |
| Step, token or cost budget exhausted | `budget_exhausted` | yes | yes, separate count |
| Infrastructure error (sandbox, image pull, verifier crash; `reward_valid` false) | `infra_error` | **no** | **always** counted and shown per harness |

Rules: infrastructure errors are excluded from pass@1 but never hidden; the Markdown report shows infra-error counts next to pass@1 (implemented). The following are Planned: flagging a comparison when an arm's infra-error rate exceeds 5%, a retry policy for such trials, and recording retries; a retried trial would keep its attempt number, and the cost of every attempt would be counted (see cost metric). Unrecognised exceptions default to `infra_error` only if Harbor marks them so; otherwise `failed`, to avoid inflating pass@1 by dropping hard tasks.

## Metrics

| Metric | Definition |
|---|---|
| pass@1 | As implemented in `evaluation/metrics.py`: solved first attempts / graded first attempts, per (dataset, harness). Averaging over k samples per task is Planned |
| Transfer gain | For a harness H: pass@1(adapter, H) minus pass@1(Base, H), paired by task. "Cross-harness" transfer gain = gain under H for an adapter trained on a different harness only |
| Tokens | Input and output tokens per trial. Aggregation exists; extraction from `agent_result.n_input_tokens` and `n_output_tokens` is Planned (issue 008) |
| Tool calls | Count of tool calls per trial, from the harness trajectory (ATIF `trajectory.json` when present); extraction Planned (issue 008) |
| Latency | Wall-clock agent-phase seconds per trial from phase timings (extraction Planned); verifier time reported separately |
| Cost per solved task | (Sum of `cost_usd` over **all** trials, including failed, timed-out, retried and infrastructure-error ones) / (number of solved trials); null if any trial lacks cost. Local models have no `cost_usd`; a configured price per token or GPU-hour is Planned (issue 008), until then cost is null and so is cost per solved task |
| Infra-error rate | infra_error trials / all trials |

**Missing values stay null, never 0.** If a harness does not report tokens, tool calls or cost for a trial, the field is null. The mean of any metric with a missing value is reported as n/a (code: `evaluation/metrics.py`, `compare.py`), because averaging over a partly known column is biased; a null is never averaged as zero. Paired ratios (tool calls, output tokens, latency) are candidate/base totals over tasks both solved, and are n/a if any value is missing.

## Experiment matrix

| ID | Arms | Harnesses | Purpose | Milestone |
|---|---|---|---|---|
| E0 | Base | Pi, OpenCode | Baseline and infra-error rate, no training | v0.1 |
| E1 | Reference Pi adapter vs Base | Pi, OpenCode | Re-measure published transfer under our pins; sanity check | v0.1 |
| E2 | Pi-only (1 seed) | Pi | Single-harness RL works at all on our stack | v0.2 |
| E3 | Joint (1 seed, small) | Pi, OpenCode | Shared-LoRA pipeline runs end to end | v0.3 |
| E4 | Base, Pi-only, OpenCode-only, Merge, Joint, Joint-mixed; >= 3 seeds | Pi, OpenCode | RQ1-RQ3 at matched budget | v0.4 |
| E5 | Same method on Qwen3.8-Flash-Next | Pi, OpenCode | RQ4 (gated) | v0.5 |

E1 results are labelled "re-measurement", not new findings.

## Manifest

Every run writes `manifest.json` (`core/manifest.py`, written at start and completed at the end).

**Recorded today** (code; exercised with the mock runner only):

- Run name, status, simulated flag, creation and finish times, error, planned and recorded trial counts.
- Seed, the full evaluation config (which carries model, inference parameters and limits) and its hash.
- Code: package version, commit SHA, **dirty flag** (the report prints "(uncommitted changes)" next to the commit; a stronger "not reproducible" marking is Planned).
- Per dataset: name, split, revision, licence, task count, hash of the task list.
- Per harness: requested version and observed versions.
- Python version, platform, installed package versions.

**Planned** (not yet recorded):

- Adapter identity and file hash; split-file hash and leakage-audit result hash.
- Container image digests; Harbor, OpenEnv, TRL, vLLM, PEFT, Transformers versions in the serving and training environments.
- Separate training, sampling and task-order seeds.
- Budget counters: rollouts, supervised tokens, optimiser steps, rows per harness.
- Hardware summary (GPU model and count, ROCm and driver versions) without host identifiers.
- Command line.

## Reproducibility: what is and is not

Reproducible (Planned for real runs): configs, splits, pins, manifests, parsing and statistics given the same raw trial results. Mock runs are seeded; we have not tested that they are bit-identical.

Not reproducible bitwise: seeded sampling under vLLM concurrent batching, floating-point reduction order on GPU, agent behaviour that depends on network, wall-clock or sandbox timing, and upstream images that may change. Seeds reduce variance but do not give identical trajectories. We therefore (a) publish raw per-trial results, (b) use several seeds and k samples, and (c) report intervals, not single numbers. A claim that a result "reproduces" means it falls within the interval of the original, not that it is identical.
