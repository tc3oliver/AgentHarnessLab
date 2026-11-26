# Qwen3.8-Flash-Next: feasibility for harness RL (v0.5, Phase D)

Status, 2026-11-26: **serving with LoRA is possible on one MI325X. Training is blocked**: the FP8 kernel transformers
needs is fetched from the Hugging Face Hub at runtime, and we do not run Hub code. No training was attempted, and
no Flash-Next adapter exists.

All probes ran on GPU 6 (renderD176), one at a time, with no network for the trainer container and no privileged
settings. Artifacts are under `/data3/users/oliver/experiments/agentlab/flashnext/` (not in git).

## The model

Read from `config.json` and a meta-device build in transformers 5.20.2. No weights were loaded for this table.

| Item | Value |
|---|---|
| Checkpoint | `/data3/models/qwen3.8-flash-next-fp8`, 172.8 GiB as vLLM loads it, FP8 e4m3 with 128×128 block scales |
| Architecture | `Qwen4ExpForConditionalGeneration` (`qwen4_exp`); text model `Qwen4ExpForCausalLM` |
| Layers | 48: linear attention (gated delta rule) with full attention every 4th layer (12 layers) |
| Parameters | Experts 120.8B (48 × 512 × (2560×1280 + 2560×640); 10 active per token; fused 3D tensors). N-gram embedding table 51.2B (20M × 2560). Total 176.9B and about 5B for everything else, both from a meta-device build that was not saved |
| Licence | Qwen Community License 1.0. Fine-tuning and derivatives are allowed, and the copyright and permission notice must go with copies and derivatives. Products above 100M monthly active users or US$20M monthly revenue must display the model name. A licensee running a Model-as-a-Service or AI Work Assistant business needs a separate licence for commercial use. Internal use is exempt only if the software, its outputs and its capabilities are not made available to any third party. Our reading, not legal advice: releasing a derived adapter would need the notice, and the project owner decides before any release |

## Probe 1: vLLM serving with LoRA (vLLM 0.33.0 ROCm, the production image digest)

- **Hypothesis:** vLLM serves the FP8 checkpoint at TP1 with `--enable-lora` and applies a LoRA adapter on the
  full-attention `q_proj`/`o_proj`.
- **Adapter:** rank 8 on the 12 full-attention layers. One copy has lora_B = 0 (it must change nothing), and one
  has random lora_B (it must change the output). Written by `probe-lora/make_adapter.py` and `make_adapter_nz.py`.

| Run | Result |
|---|---|
| Without LoRA, AITER FP8 MoE | Starts. Weights 171.9 GiB, loaded in 25 s |
| `--enable-lora`, AITER FP8 MoE | **Fails at startup.** `FP8 MoE backend AITER does not support the deployment configuration … quantization scheme` (`serve-lora.log`) |
| `--enable-lora`, `VLLM_ROCM_USE_AITER_MOE=0` (Triton FP8 MoE) | Starts, 175.5 GiB |
| Identity adapter vs base | Same text and max \|Δ logprob\| 0.0 over 92 greedy tokens (`identity.json`) |
| Random-B adapter vs base | max \|Δ logprob\| 0.20 over the first 10 tokens (identity: 0.0), so the adapter is applied. The full 64-token greedy texts are not identical, although their first 120 characters match (`nonidentity.json`) |
| Decode speed, Triton MoE, 92 tokens | warm runs 114 tok/s base, 73 tok/s with the adapter. First runs: 79 and 56 tok/s, the LoRA one including Triton JIT |

LoRA serving therefore works only on the Triton MoE backend. Production's tuned AITER MoE path is not available
with LoRA. The decode figures come from two 92-token requests per model, not a benchmark.

## Probe 2: one LoRA training step (trainer image `agentlab-trainer:trl1.19.0-openenv0.14.0`)

- **Hypothesis:** transformers 5.20.2 with PEFT 0.22 loads the FP8 checkpoint onto one GPU and runs a LoRA
  forward and backward on `q_proj`/`o_proj` at 4k and 16k tokens.
- **Script:** `probe-train/step.py`, log in `probe-train/step.log`.

| Step | Result |
|---|---|
| Load | Works. 171 s, 169.4 GiB on the GPU, experts as `FP8Experts`, 2.26M trainable LoRA parameters |
| Forward at 4k and 16k tokens | **Fails:** `finegrained-fp8 kernel unavailable: kernels is either not installed or uses an incompatible version (0.17.2 <= version < 0.18.0)` |
| Linear attention | transformers warns that it falls back to the reference PyTorch `chunk_gated_delta_rule` because `flash-linear-attention` is not installed |

The `kernels` package downloads compiled kernels from the Hugging Face Hub when they are first used. For the 27B
pilot we replaced TRL's Hub FlashAttention kernel with the image's own build for the same reason (pilot rung 2), so
the package was not installed here. The error text alone ("not installed or uses an incompatible version") does not tell the two apart; the image has no `kernels` package.

## What it would take

Ordered by effort. Each step is a decision for the project owner, because each one changes the security posture
or the GPU budget.

1. **Vendor the FP8 kernel.** Review the source of the `finegrained-fp8` kernel, then build it into the trainer
   image from a pinned commit, with no Hub access at runtime. Separately, check that it supports gfx942 and
   e4m3fnuz. Also install `flash-linear-attention` from a pinned release; it provides the Triton gated delta rule.
2. **Dequantizing fallback.** A local `FP8Experts` and `FP8Linear` forward that dequantizes 128×128 blocks to BF16
   per call. This needs no external code. It is slow for 512 experts per layer, but only the 10 active experts per
   token are touched.
3. **BF16 copy.** About 354 GB (2 bytes × the unverified 176.9B total), so at least two GPUs with FSDP for the frozen base, plus activation memory. The
   copy would have to be produced and stored outside git.

Two further constraints apply to all of them:
- Rollouts need vLLM with the Triton MoE backend, so throughput will be lower than the production replicas.
- TRL's tree attention and recurrent patches were written for Qwen3.5-style models. They have not been checked
  against `qwen4_exp`, whose layers also have hyper-connections and an n-gram embedding.

## Recommendation

Keep v0.5 as evaluation-only until there is a reviewed FP8 kernel (option 1), and until the 27B work shows a
training signal on a licence-cleared training set. Flash-Next serving is ready for evaluation runs today, with or
without an adapter.
