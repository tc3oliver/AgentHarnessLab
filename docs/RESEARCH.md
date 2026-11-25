# Research plan

Project goal: reproducible cross-harness agent post-training. Status labels used everywhere in these docs:
**Verified** (we ran it), **Planned** (designed, not run), **Unverified** (believed from reading, not run).
Today nothing in this plan has been run on a GPU. Upstream facts and versions are in [UPSTREAM.md](UPSTREAM.md).

## Research questions

1. **RQ1 Shared LoRA.** Can one LoRA improve two harnesses (Pi and OpenCode) at the same time?
2. **RQ2 Joint vs merge.** Does Joint Multi-Harness RL beat per-harness training followed by adapter merging, at matched budget?
3. **RQ3 Efficiency.** Can tool calls, tokens, latency and cost per solved task fall, not only pass@1 rise?
4. **RQ4 Generations.** Does the method transfer across model generations (for example Qwen3.8-27B to a later or different model)?

The method is meant to be model-, harness- and hardware-agnostic. That is a design goal (Planned), not a result.

## Prior work, stated plainly

Details and sources are in [UPSTREAM.md](UPSTREAM.md#reference-work-so-we-do-not-claim-its-results-as-new).

- Cross-harness transfer is already reported: a Pi-trained adapter improved OpenCode on Terminal-Bench 2.1.
- Adapter merging across harnesses is already reported (PEFT `cat`, rank 96).
- Joint multi-harness RL is already reported at small scale (2B-class models, four harnesses, single seed, unequal exposure).
- The reference Pi recipe selected its checkpoint on benchmark tasks, so its numbers are not selection-free.

Our contribution, if any, is narrower: a **matched-budget, multi-seed** comparison of Base, specialists, merge and joint training at 27B, with a leakage-audited data split and per-harness cost accounting. We did not find this comparison in the sources we read; absence from them is not proof it does not exist. We do not claim the reference results as ours.

## Arms

| Arm | Training | Status |
|---|---|---|
| Base | none | Planned |
| Pi-only | RL with every group run under Pi | Planned |
| OpenCode-only | RL with every group run under OpenCode | Planned |
| Merge | Pi-only and OpenCode-only adapters combined (method and weight fixed before test, see below) | Planned |
| Joint | one shared LoRA; each task repeated once per harness, so groups are Task x Harness | Planned |
| Joint-mixed (ablation) | like Joint, but a group mixes rollouts from both harnesses and the advantage is standardised across them | Planned |

Joint uses stock GRPO group standardisation: repeating a task once per harness already yields Task x Harness groups ([UPSTREAM.md](UPSTREAM.md), TRL). Joint-mixed isolates whether per-harness advantage matters.

Merge method is chosen on the validation split only (candidates: concatenation, weighted average; weight grid fixed in the config before training). The reference work picked its weight on the benchmark; we do not.

## Budget matching

Compare arms at equal cost along two axes, both logged per run:

- **Total rollouts** (trajectories sampled, including those later filtered).
- **Supervised tokens** (tokens with loss mask 1 that reach the optimiser).

Rules:

- Joint gets N rollouts split evenly across harnesses. Each specialist gets N/2 per harness-arm only if the comparison is "same total"; a merge uses **two** specialists, so Merge consumes the budget of both. Report both framings:
  - **Equal total**: Joint N, Pi-only N/2, OpenCode-only N/2, Merge = those two (total N).
  - **Equal per-specialist**: Joint N, each specialist N (Merge total 2N). This favours Merge; report it as an upper bound for the merge route.
- Optimiser steps, learning rate, LoRA rank and sampling parameters are identical across arms unless a deviation is listed in the experiment manifest.
- If supervised tokens diverge by more than 10% across arms at equal rollouts, report results also at equal supervised tokens (threshold is a Planned default).

## Hypotheses and decision rules

**Power caveat.** The test sets total about 140 tasks (51 SWE-bench Pro hard plus 89 Terminal-Bench 2.1), and each harness is evaluated on them separately. Intervals are wide at this size: the reference card's +16 points on 86 paired tasks came with roughly a +/-9 point interval. A 2-point margin is far below what one seed on about 140 tasks can resolve, so H2 will often come out inconclusive unless seeds and k samples shrink the noise; we report that outcome as is and do not lower the bar.

Primary metric: pass@1 on the held-out test set, per harness (see [EXPERIMENTS.md](EXPERIMENTS.md)). All thresholds below are set before any run and recorded in the config.

- **H1 (RQ1).** The Joint adapter beats Base on both Pi and OpenCode test sets. *Supported* if for both harnesses the paired gain over Base is positive and the lower bound of its 95% bootstrap CI is above 0 (pooled over seeds). *Refuted* if either harness has a gain whose upper CI bound is below 0. Otherwise *inconclusive*.
- **H2 (RQ2).** Joint beats Merge at matched budget. Compare the mean of per-harness gains. *Joint wins* if the paired difference CI excludes 0 in Joint's favour and exceeds a pre-set margin of 2 pass@1 points. *Merge wins* by the mirror rule. Otherwise *no detectable difference*, which we report as such, not as a tie in effect.
- **H3 (RQ3).** Cost per solved task falls. *Supported* if, on tasks solved by both Base and the trained arm, median tool calls or tokens fall with a CI excluding 0, **and** cost per solved task over all tasks (failed attempts included) does not rise. A fall driven only by more failures is not support.
- **H4 (RQ4).** The Joint-over-Base gain on a second model generation has the same sign for both harnesses and a CI overlapping the first generation's gain. Weak by design: it tests transfer of the method, not identical effect size. Requires v0.5 or a second dense model (Planned, gated).

Negative and null outcomes are published with the same prominence.

## Confounders and how we handle them

| Confounder | Why it matters | Handling |
|---|---|---|
| History rewriting row weight | One rollout can become several training rows (about 8 for Claude Code in the multi-harness article); a harness that rewrites or compacts context gets more weight in a joint loss | Log rows and supervised tokens per harness; report an arm with per-harness normalisation as a sensitivity run |
| Context compaction | Pi compacts context, OpenCode does not; pass@1 is not comparable across harnesses | Compare only within a harness; transfer gain is a within-harness difference |
| Checkpoint selection on benchmarks | The reference recipe chose a checkpoint by looking at benchmark tasks | Select on validation split only; evaluate the final and the selected checkpoint on test once |
| Tools disabled in OpenEnv OpenCode | OpenEnv trains OpenCode with `task`, `question`, `webfetch` disabled | Evaluate with the same tool set as training, and also report an eval with defaults as a robustness check |
| Harness/Harbor version pinning | OpenEnv caps Harbor below 0.26; OpenCode v2 needs Harbor 0.27 | One Harbor version per comparison; v0.1 pins 0.25.0 and OpenCode v1; numbers not comparable to the release blog |
| Training-data contamination | Terminal-Bench 2.1 holds training canaries; TermGrade card forbids training use | See [DATASETS.md](DATASETS.md) leakage audit |
| Non-bitwise sampling | vLLM under concurrency is not deterministic | Multiple seeds and repeated evaluation; see reproducibility in [EXPERIMENTS.md](EXPERIMENTS.md) |

## Threats to validity

- **Internal:** unequal exposure between harnesses, checkpoint selection, infrastructure failures differing per harness (excluded from pass@1 but reported), LoRA rank limiting the merge.
- **Construct:** pass@1 under one harness version is not "agent quality"; harness updates change the target. We pin versions and record them.
- **External:** one model family, two harnesses, Go/Python-heavy training tasks, one hardware class. Results may not carry to other languages, harnesses or scales.
- **Statistical:** small test sets (86-89 paired tasks in Terminal-Bench 2.1) give wide intervals; differences of a few points will often be inconclusive. We say so rather than rank arms.
- **Evaluation noise:** a task's outcome varies by sample; we use repeated evaluation per task.

## Statistics

- **Unit and pairing.** The unit is the task. All arm comparisons are paired on the same tasks, same harness, same image digest.
- **Per-task score.** Mean over k evaluation samples per task (k fixed in config; Planned default 4); pass@1 is the mean of per-task scores. The current code computes pass@1 over first attempts only (one sample per task); k-sample averaging is Planned. Infrastructure-error trials are excluded per rule in [EXPERIMENTS.md](EXPERIMENTS.md).
- **Tests.** For binary per-task outcomes (k=1): exact two-sided sign test on discordant pairs, equivalently exact McNemar. For averaged scores: paired bootstrap.
- **Intervals.** 95% percentile bootstrap CIs, 10,000 resamples, resampling tasks and, where available, seeds hierarchically (seeds first as clusters when n_seeds >= 3).
- **Seeds.** At least 3 training seeds per arm for v0.4 (Planned). With fewer seeds, results are labelled single-seed and no ranking is claimed.
- **Multiplicity.** Primary tests are H1 (2 harnesses) and H2; control with Holm across these. Everything else is exploratory and labelled so.
- **Reporting.** Effect sizes with CIs first, p-values second; report discordant-pair counts so readers can recompute.
