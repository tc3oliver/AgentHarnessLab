# Roadmap

Statuses: **Verified** (we ran it), **Planned**, **Unverified**. As of the date in [UPSTREAM.md](UPSTREAM.md), the schemas, config, reports, mock and Harbor runners and Harbor smoke tasks exist. Work items are in [issues/README.md](issues/README.md). Research design: [RESEARCH.md](RESEARCH.md).

## v0.1 Reproducible Evaluation

- **Exists today (no model-backed run yet):** the Harbor runner with Pi and OpenCode configurations, config validation with revision pins, local dataset loading, leakage-audit core, manifests, the mock runner, metrics aggregation, paired comparison with an exact sign test, Markdown reports, Harbor oracle/nop smoke tasks. Nothing has run against a real model or dataset.
- **Scope:** run Pi and OpenCode through Harbor from one config against a vLLM endpoint; parse results; manifests; pinned data splits and leakage audit; baseline (E0) and reference-adapter re-measurement (E1); report with CIs.
- **Acceptance:** E0 and E1 complete on the validation split; every run has a complete manifest; infra-error rate reported per harness; a rerun from the manifest lands inside the first run's interval; statistics code passes unit tests with known answers.
- **Test method:** unit tests with the mock runner; Harbor oracle/nop smoke tasks; validation ladder rungs 0-3 ([HARDWARE.md](HARDWARE.md)); rerun comparison.
- **Artifacts:** result schema and parser, manifests, split files and audit report, E0/E1 reports, pinned environment lock.
- **Depends on:** a ROCm vLLM server that passes rungs 0-2; access to pinned datasets.
- **Go/no-go risks:** LoRA serving or hybrid-model serving fails on ROCm (fallback: other hardware, same configs); Harbor 0.25.0 vs 0.27.0 pin makes OpenCode numbers incomparable to published ones (accepted, documented); unclear dataset licences limit what can be released.

## v0.2 Single-Harness RL

- **Scope:** reproduce the shape of the reference recipe: GRPO with LoRA under Pi only, via TRL's async GRPO and OpenEnv's Harbor rollouts; checkpoint selection on validation.
- **Acceptance:** rungs 4-7 pass; one training run completes; validation pass@1 under Pi is reported against Base with a CI; no test-set use in selection.
- **Test method:** tiny-loop tests, then a full run; compare to Base with the paired tests in [RESEARCH.md](RESEARCH.md#statistics).
- **Artifacts:** training config, adapter, training logs (rewards, rows, supervised tokens), validation report.
- **Depends on:** v0.1; the TRL/OpenEnv/Harbor version combination tested together (known conflicts in [UPSTREAM.md](UPSTREAM.md#constraints)).
- **Go/no-go risks:** training on ROCm unstable or too slow; the TRL example pins an old OpenEnv; no measurable gain (then report a null and stop before v0.3).

## v0.3 Multi-Harness RL

- **Scope:** one shared LoRA trained on Pi and OpenCode rollouts; each task repeated once per harness so advantages are per Task x Harness; a routing session factory with explicit harness assignment (not `seed % n`); per-harness logging.
- **Acceptance:** a Joint run finishes; both harnesses contribute rollouts in the configured ratio; rows and supervised tokens per harness are logged; routing survives a checkpoint resume.
- **Test method:** unit tests for routing and group construction; a tiny joint loop; a resume test.
- **Artifacts:** routing factory, joint config, per-harness logs, validation report for E3.
- **Depends on:** v0.2.
- **Go/no-go risks:** OpenCode rollouts via OpenEnv have tools disabled (evaluation must match); compaction over-weights Pi rows; Harbor version constraints between harnesses; training instability with two harnesses.

## v0.4 Research Benchmark

- **Scope:** Base, Pi-only, OpenCode-only, Merge, Joint (and Joint-mixed ablation) at matched budget, at least 3 seeds each, test sets run once.
- **Acceptance:** all arms complete with the same budget accounting; H1-H3 each get a decision per the rules in [RESEARCH.md](RESEARCH.md#hypotheses-and-decision-rules), including "inconclusive"; raw trial data and manifests published (subject to licences).
- **Test method:** statistics pipeline on raw results; budget-audit script that checks rollouts and supervised tokens per arm.
- **Artifacts:** adapters (if licences allow), full results, report, reproduction instructions.
- **Depends on:** v0.3; GPU time for roughly 5 arms x 3 seeds (estimate not yet made).
- **Go/no-go risks:** compute budget; small test sets give wide intervals; merge method choice; dataset licensing blocks release of artifacts.

## v0.5 Large MoE (Qwen3.8-Flash-Next)

- **Scope:** repeat E4 in reduced form on Qwen3.8-Flash-Next for RQ4. Gated model (`qwen-community-1.0`, not OSI).
- **Acceptance:** vLLM serves it on the target hardware; if trainable, a Joint and a Base comparison with CIs.
- **Test method:** validation ladder rungs 0-7 repeated.
- **Artifacts:** configs, results, a note on what failed.
- **Depends on:** v0.4; gated model access; a training path. TRL has no `qwen4_exp` reference while vLLM does ([UPSTREAM.md](UPSTREAM.md#constraints)), so training needs either TRL support, a port, or another trainer (SkyRL is an option, not adopted).
- **Go/no-go risks:** no trainer support (then v0.5 becomes evaluation-only); memory for MoE on 4 GPUs; licence terms for releasing derived adapters.
