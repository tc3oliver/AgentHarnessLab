# Hardware plan

Target: one node with 4 AMD Instinct MI325X GPUs, 256 GB HBM each. Serving (rungs 0 to 2, partly) was run on one MI325X on 2026-11-25 ([report](reports/overnight-development.md)); every other statement is **Planned** or **Unverified**, and LoRA forward/backward on MI325X is explicitly **Unverified** ([UPSTREAM.md](UPSTREAM.md#constraints), item 7). GPU assignment is configuration (device lists in the experiment config), never hard-coded.

## Memory arithmetic (estimate)

For Qwen3.8-27B (about 27B parameters; hybrid with 3 linear-attention layers per full-attention layer):

| Item | Estimate | Basis |
|---|---|---|
| bf16 weights | about 54 GB | 27e9 x 2 bytes |
| LoRA r=32 on seven projection types | well under 1 GB for weights and Adam states | small relative to base; exact count depends on dimensions, not computed here |
| Trainer activations, long agent context, gradient checkpointing on | tens of GB, strongly dependent on sequence length | rough; to be measured |
| vLLM KV cache | only the full-attention quarter of layers grows with context; linear-attention layers keep a fixed state | architecture reading; per-token size not computed |

These are order-of-magnitude guesses. A 27B model fits in one 256 GB GPU for either role by this arithmetic; the ladder below replaces the estimates with measurements. The reference recipe used 2 GPUs (one vLLM, one trainer), which supports the same two-role split.

## Candidate layouts

| Layout | Inference | Trainer | Notes |
|---|---|---|---|
| A (2 GPUs) | 1 GPU | 1 GPU | Mirrors the reference recipe. Two such jobs can run side by side on 4 GPUs (for seeds) |
| B (4 GPUs) | 2 GPUs, tensor parallel | 2 GPUs | More rollout throughput; TP on ROCm with this model is Unverified |
| C (4 GPUs) | 1 GPU | 3 GPUs | Only if training is the bottleneck and the trainer scales; Unverified |

Constraints: the LoRA update path needs a shared filesystem between trainer and server and no data-parallel replicas of the server. Multi-seed throughput (A, twice) is usually worth more than one faster run, to be confirmed by measurement.

## ROCm risk list

1. **Wheel selection.** vLLM publishes ROCm wheels for specific Python versions; a wrong Python silently installs the CUDA wheel. Fallback: use the vLLM ROCm container image. Check `torch.version.hip` is set.
2. **AITER attention kernel.** TRL uses `kernels-community/aiter-flash-attn` on ROCm. It may not support the linear-attention or hybrid layers or the head dimension. Fallback: SDPA/eager attention, slower and more memory.
3. **LoRA weight sync path.** Relies on the adapter-on-disk and `/v1/load_lora_adapter` path, which avoids NCCL-style transfer engines, but runtime LoRA loading with this hybrid model on ROCm is Unverified. Risk: slow reloads or stale adapters; verify the served adapter hash after each update.
4. **Device ordering.** HIP device indices can differ from the order shown by `amd-smi`. Select devices by a verified mapping (for example by UUID or bus ID) and log it in the manifest, or training and serving can land on the same GPU.
5. **Hybrid linear-attention training.** Gated DeltaNet layers need `transformers>=5.15` in TRL; kernels for them on ROCm (Triton or fallback) may be missing or slow. Check numerical parity against a CPU or reference run on a small input.
6. **Prefix caching.** Qwen3.8 needs `--mamba-cache-mode align` for prefix caching in vLLM. Wrong flags can silently give wrong outputs or no caching; test with and without and compare outputs on a fixed prompt.
7. **Version ranges.** TRL 1.18.2 declares `vllm<0.34`; use a combination we have tested, not the newest of each.

## Validation ladder

Each rung must pass before the next. Record command, versions and result in the manifest.

| Rung | Test | Pass criteria |
|---|---|---|
| 0 | Device inventory | GPUs enumerate; HIP-to-physical mapping recorded; `torch.version.hip` set; a bf16 matmul runs |
| 1 | vLLM serves the base model | Server starts; 20 fixed prompts return text; greedy output stable across 2 restarts; prefix-cache flag verified |
| 2 | Harness smoke | Pi and OpenCode each complete one trivial Harbor task against the endpoint; trial parses into the result schema |
| 3 | Mini evaluation (E0 subset) | 10 tasks x 2 harnesses finish; infra-error rate under 10%; token and latency fields populated |
| 4 | LoRA forward/backward | One step on a 27B (or small same-architecture) model with LoRA; loss finite; no NaN over 20 steps; peak memory recorded |
| 5 | Adapter round trip | Trainer saves adapter; server loads it by `/v1/load_lora_adapter`; outputs differ from base; hash matches |
| 6 | Tiny RL loop | 5 optimiser steps with 2 tasks x 2 harnesses; reward and rows per harness logged; no deadlock; staleness bound respected |
| 7 | Stability run | 100 steps without crash; memory flat; throughput recorded; resume from checkpoint continues group routing correctly |

Failure at any rung is reported with the fallback tried and its result. Throughput and memory numbers measured here replace the estimates above.
