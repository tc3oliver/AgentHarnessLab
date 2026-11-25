# Experiments

Research design is in [RESEARCH.md](RESEARCH.md); data rules in [DATASETS.md](DATASETS.md); upstream facts in [UPSTREAM.md](UPSTREAM.md). Status: the mock runner, result and manifest schemas, config validation, metrics, paired comparison and Markdown reports exist in `src/`; Harbor smoke tasks (oracle, nop) exist. No model-backed run has happened. Everything below about real runs is **Planned** unless it says it is implemented.

## Evaluation protocol

1. An experiment config names: model (Hub ID + revision), optional adapter (path or revision), dataset (ID + revision; a split-file hash is Planned), harness (`pi` or `opencode`) and its version, inference parameters, seed, attempts per task (`n_attempts`), per-trial limits. The Harbor version is in the runner config and checked at preflight.
2. Each (task, harness, attempt) is one Harbor trial. `HarborRunner` runs Harbor as a subprocess, one job per (harness, attempt), and parses each `result.json` into the project result schema. It ran the smoke tasks; no model-backed run has happened.
3. Evaluation uses the same harness, tool set and version as training for that arm. Pi and OpenCode are never compared with each other on pass@1 (they differ in context compaction); only within a harness.
4. The serving endpoint is an OpenAI-compatible server, and the key is passed by environment variable name. **Sampling is declared, not enforced:** harnesses choose their own request parameters (neither Pi nor OpenCode v2 sent a temperature in our runs), so set `--override-generation-config` and `--default-chat-template-kwargs` on the server and record them in `server_args`. No seed reaches the sampler, so `seed` is null in real results.
5. For adapters, vLLM serves the base model with the adapter loaded; the adapter is identified in the manifest by file hash (Planned).
6. Test sets are run once per final configuration.

## Harbor status to outcome rules

Each trial maps to exactly one outcome (`evaluation/harbor_results.py`; the version, no-result and no-usage rules are in `evaluation/harbor.py`). Rows marked R are tested on results recorded from real Harbor 0.25.0 and 0.27.0 runs; the others on edited copies.

| Trial situation | Outcome | In pass@1 denominator |
|---|---|---|
| Verifier reward at or above the threshold (R) | `solved` | yes |
| Verifier reward below the threshold (R), or the model refused the task | `failed` | yes |
| `AgentTimeoutError` (R) and not solved | `timeout` | yes |
| Context or output limit error and not solved | `budget_exhausted` | yes |
| `NonZeroAgentExitCodeError` (R on 0.27.0) and not solved | `agent_error` | yes |
| Verifier timeout (R), missing (R), empty or unparsable (R) reward, or missing reward key | `verifier_error` | **no** |
| Sandbox (R), setup timeout (R on 0.25.0), provider, cancelled or unknown exception; no result; harness version differs from the pin | `infra_error` | **no** |

Rules:

- After a graded exception the verifier decides: a trial that timed out but passes is `solved`. Harbor does the same, except that 0.25.0 does not accept the reward after a non-zero agent exit; we do, so that both versions are treated alike.
- Ungraded outcomes are never hidden: reports show infra, verifier and agent error counts next to pass@1.
- Unknown exceptions are `infra_error`. Harbor 0.25.0 does the same; 0.27.0 would accept their reward. This can drop hard tasks, so a run with more than 5% ungraded trials must not be reported as a result. The automatic check is Planned.
- When an agent command exits non-zero, Harbor picks the exception type by searching the whole output, including what tools and the model wrote, for phrases such as "rate limit". If the harness itself recorded a normal end of its last turn (OpenCode: `step_finish` with reason `stop` and no error event; Pi: stop reason `stop`), such a type counts as `agent_error` when unsolved, never as `infra_error`.
- A policy could in principle avoid a failure by making the verifier hang. Verifier errors need a manual look before a run is reported.
- Harbor retries are off (`max_retries: 0`): a retry would hide the cost and failure of the first try.
- A Pi run stopped by `max_turns` has no exception in Harbor and shows up as `failed`.
- The endpoint is probed before each run and after each job, so an endpoint that is still down at the end of a job fails the run. A shorter outage does not.
- A model-driven trial that would be `failed` or `agent_error`, recorded no model usage, and whose trajectory shows no text or tool call by the agent is `infra_error`: typically the sandbox could not reach the endpoint.
- A failure before the agent started (for example while installing the harness) is `infra_error`.
- Other harness exit errors are graded even if the cause was a brief endpoint problem; read the `error` field.

## Metrics

| Metric | Definition |
|---|---|
| pass@1 | As implemented in `evaluation/metrics.py`: solved first attempts / graded first attempts, per (dataset, harness). Averaging over k samples per task is Planned |
| Transfer gain | For a harness H: pass@1(adapter, H) minus pass@1(Base, H), paired by task. "Cross-harness" transfer gain = gain under H for an adapter trained on a different harness only |
| Tokens | Input and output tokens per trial from Harbor `agent_result`. Harbor sums missing usage as 0, so 0 input tokens is read as unknown. OpenCode requests outside the agent loop (session title) are not counted |
| Tool calls | Counted in the ATIF `trajectory.json`; null without one, or when OpenCode started a subagent whose nested calls ATIF omits |
| Latency | Agent-phase wall clock from Harbor timings; excludes sandbox setup and verifier |
| Cost per solved task | Sum of `cost_usd` over **all** trials / solved trials; null if any trial lacks cost. `cost_usd` uses only the prices in the config, because harnesses report 0 for models they have no price for. GPU-hour pricing is Planned (issue 008) |
| Ungraded rate | (infra_error + verifier_error) / all trials |

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

**Recorded today** (also: `runtime` with Harbor, Docker, served model and engine version, read at preflight):

- Run name, status, simulated flag, creation and finish times, error, planned and recorded trial counts.
- Seed, the full evaluation config (which carries model, inference parameters and limits) and its hash.
- Code: package version, commit SHA, **dirty flag** (the report prints "(uncommitted changes)" next to the commit; a stronger "not reproducible" marking is Planned).
- Per dataset: name, split, revision, licence, task count, hash of the task list.
- Per harness: requested version and reported versions (for Pi and OpenCode v1 Harbor repeats the request).
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
