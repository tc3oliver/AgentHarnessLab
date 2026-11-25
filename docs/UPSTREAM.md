# Upstream snapshot

Facts read from upstream source, model/dataset cards and package metadata on **2026-11-25**.
"Read" means read in source or docs; "Run" means executed by us. Nothing here was run on a GPU.

## Versions

| Project | Release | Commit read | Licence |
|---|---|---|---|
| TRL | 1.18.2 (Python >=3.11) | `7bdf0cf3` | Apache-2.0 |
| Harbor (`harbor`) | 0.27.0 (Python >=3.12) | `90f2ee3c` | Apache-2.0 |
| OpenEnv (`openenv`; `openenv-core` is an older name) | 0.14.0 | `3659dc73` | BSD-3-Clause |
| vLLM | 0.34.0 | `d51a5147` | Apache-2.0 |
| SkyRL | 0.5.0 | `2f9e5e84` | Apache-2.0 |
| PEFT | 0.22.0 | not read | Apache-2.0 |
| Pi (`@earendil-works/pi-coding-agent`) | 1.6.0 | not read | MIT |
| OpenCode v1 (`opencode-ai`) / v2 (`@opencode/cli`) | 1.19.6 / 2.4.1 | not read | MIT |

Pinned Hub revisions: `Qwen/Qwen3.8-27B@37561816e66b5b9153b1b64c10968c18c1e6f4a0` (Apache-2.0),
`harness-hub/Qwen3.8-27B-pi-adapted@41396a9f14d9c1a1bf5bee4fb89e9dddadaeae7e` (Apache-2.0),
`Qwen/Qwen3.8-Flash-Next@812d96e10a0dd82b69d749e68693698cf6c36daa` (gated; `qwen-community-1.0`, not OSI).

## Reference work (so we do not claim its results as new)

- **Pi adapter** (model card): LoRA r=32, alpha=64, on q/k/v/o/gate/up/down_proj. The release blog says
  `all-linear`; `adapter_config.json` lists those seven modules. Step 160, lr 2e-5, 8 rollouts per task,
  temperature 0.8, thinking off, 50 agent steps and 1,800 s per rollout, 2x B200 (one vLLM, one trainer).
  Reported pass@1 under Pi: SWE-bench Pro hard-51 39.2% -> 64.7%; Terminal-Bench 2.1 (86 paired tasks) 39.5% -> 55.8%.
  The checkpoint was chosen by looking at SWE-bench Pro and an 18-task Terminal-Bench subset, so those numbers are not
  selection-free. The training script is TRL `examples/async_grpo_harbor`; its efficiency weight default is 0.3,
  the card says 0.1.
- **Cross-harness transfer is already reported**: the Pi adapter under OpenCode 44.8% -> 54.0% on Terminal-Bench 2.1
  (OpenCode specialist: 46.4% -> 52.4%).
- **Adapter merging is already reported**: PEFT `combination_type="cat"` over pi/hermes/opencode, rank 96, weight 1/2 best;
  pairwise update cosine about 0.01-0.02. Weight chosen on Terminal-Bench 2.1.
- **Joint multi-harness RL is already reported at small scale** ("The ultimate guide to multi-harness RL",
  Space `FineEnvs/multi-harness-rl`): LFM2.5-2.6B and Qwen3.5-2B, four harnesses (OpenCode, Claude Code, Codex,
  mini-SWE-agent), harness rotated across GRPO groups, every group single-harness. Joint vs OpenCode-only differed by
  1.9 points (within noise); single seed, unequal exposure, "observational" in the authors' words.
- **Not found in the sources we read**: joint RL vs specialists vs merged adapters at 27B with matched rollout budgets
  and several seeds. That is the gap this project targets. Absence from these sources is not proof of novelty.

## Reusable pieces

- **Harbor**: tasks, sandboxes, agents, verifiers, retries. `harbor run -c job.yaml`; `harbor.job.Job.create(JobConfig)`;
  per-trial `result.json` is a `TrialResult` (`verifier_result.rewards`, `agent_result.n_input_tokens/n_output_tokens/cost_usd`,
  `exception_info`, `agent_info.version`, `task_checksum`, phase timings) plus `lock.json` and optional ATIF `trajectory.json`.
  **Run**: 0.27.0 installed, its `hello-world` oracle passed in local Docker with reward 1.0.
  0.27.0 has agents `pi`, `opencode` (v1) and `opencode-v2`. `TrialResult.reward_valid` excludes infrastructure failures.
  `AgentConfig` has `base_url`, `model_api_key_name`, `model_api_format`, `kwargs`.
  `Pi` requires `model_api` (`openai-completions`) and an API-key *environment variable name* for a custom endpoint;
  `PiOptions` has `max_turns`, OpenCode v1 options do not.
- **OpenEnv**: `openenv harbor rollout|serve` puts a capture proxy between the agent and the engine and returns engine
  token ids, logprobs and loss masks. Harness and sandbox are chosen per rollout. Its `pi` and `opencode` seams are marked
  `validated`; there is **no `opencode-v2` seam**. OpenEnv trains OpenCode with the `task`, `question` and `webfetch` tools disabled.
- **TRL**: `trl.AsyncGRPOTrainer` is stable; `trl.experimental.async_grpo.openenv_harness.HarnessAsyncGRPOTrainer` is
  experimental. One group = one dataset row x `num_generations`; `compute_advantages` standardises within a group.
  So repeating each task once per harness already gives **Task x Harness** groups with no GRPO change.
  Missing piece: TRL forwards only `prompt` and `seed=group_id` to the session factory, and `HarborSessionFactory`
  holds one `harness`. Joint training needs a small routing factory. `group_id` restarts at 0 on resume while the row
  index does not, so routing by `seed % n_harnesses` is unsafe across resumes.
- **SkyRL**: has a Harbor integration and a ROCm Tinker example (built on `vllm/vllm-openai-rocm:v0.31.0`). Alternative backend, not adopted.

## Constraints

1. **Harbor version conflict (resolver checked).** Installing `openenv[harbor]==0.14.0` resolves `harbor==0.25.0`;
   OpenEnv main caps `harbor<0.26`. Harbor 0.25.0 has no `opencode-v2`. Training and evaluation must use one Harbor version
   per comparison, so v0.1 pins 0.25.0 and OpenCode v1. The release blog used OpenCode 2.2.7 and Pi 1.5.2, so OpenCode
   numbers will not be comparable with it.
2. **The TRL example pins OpenEnv 0.7.0** and needs `envs/` from its source checkout on `PYTHONPATH`
   (`harbor_env.harness` is not in the wheel). Newer OpenEnv with it is untested by us.
3. TRL 1.18.2 (release) declares `vllm>=0.23,<0.34`; main declares `<0.35`. vLLM 0.34.0 is outside the release's range.
4. Agent-owned loops need full-vocabulary sampling in TRL (`top_p=1`, `top_k` off).
5. vLLM weight transfer engines are NCCL/IPC/RDT-named. The **LoRA path avoids them**: TRL publishes the adapter to disk and
   calls `/v1/load_lora_adapter` (needs `--enable-lora`, `VLLM_ALLOW_RUNTIME_LORA_UPDATING=1`,
   `--max-loras >= max_staleness + 2`, a shared filesystem, no data-parallel replicas).
6. Qwen3.8-27B is `qwen3_5`: hybrid, 3 linear-attention layers per full-attention layer. TRL supports gated DeltaNet
   layers with `transformers>=5.15`. TRL has no `qwen4_exp` (Flash-Next) reference; vLLM does.
7. ROCm: vLLM publishes wheels for ROCm 10.0 / Python 3.14 (a wrong Python silently installs the CUDA wheel) and
   `vllm/vllm-openai-rocm` images, some on ROCm 7.2. MI300-class gfx942 is listed. TRL documents ROCm and uses
   `kernels-community/aiter-flash-attn` there. LoRA forward/backward on MI325X: **Unverified**.
8. Qwen3.8 prefix caching in vLLM needs `--mamba-cache-mode align` (Pi adapter card).

9. History rewriting forks one rollout into several training rows (about 8 for Claude Code in the multi-harness article).
   Harnesses that compact context (Pi does, per the release blog) may be over-weighted in a joint loss; log rows and
   supervised tokens per harness.
10. The release blog notes Pi compacts context and OpenCode does not, so pass@1 must not be compared *across* harnesses,
    only within one harness.

## Datasets

See [DATASETS.md](DATASETS.md) for rules. Facts:

| Dataset @ revision | Contents | Licence | Notes |
|---|---|---|---|
| `harness-hub/scale800-harbor@65940b91855c085398f24c010068da6f724074d5` | 750 Harbor tasks, 22 repositories (max 40 each), Go and Python, tests and solutions included | **none declared** | Card says "Private", but it downloads anonymously. Images on `ghcr.io/younesbelkada/scale800` |
| `harness-hub/scale800-heldout-harbor@754c8e0121faa0a5a08448e64a0c304e0a4fafec` | **empty** (only `.gitattributes`); the scale800 card describes 97 tasks from 5 other repositories | none declared | Not usable. Validation has to be split from scale800 by repository |
| `harness-hub/termgrade-train-harbor@151205e3714d8d1cec6b7d5770d344853e11d7aa` | 904 tasks, no repository identity | Apache-2.0 | Card asks to keep it private and out of training corpora; the Pi adapter trained on 300 of them |
| `ScaleAI/SWE-bench_Pro@2d52cb3df914a3fcf80c7f66738b3a88ae37fc50` | v2 642 tasks, `hard` 51, `v1` 731; 11 repositories | tooling MIT; task content keeps upstream repo licences | Harbor tasks in `scaleapi/SWE-bench_Pro-os` `v2/tasks`. `harness-hub/swebench-pro-v2-hard51-harbor` is not accessible |
| `harborframework/terminal-bench-2.1@3e235dff6880252a587fa479c09bcb1e16edf2eb` | 89 Harbor tasks | Apache-2.0 | Contains training canaries. Source `harbor-framework/terminal-bench-2-1@7131e43` |

TermGrade has no repository field, so repository-level leakage cannot be checked for it: use task-family and content-hash checks and say so.
