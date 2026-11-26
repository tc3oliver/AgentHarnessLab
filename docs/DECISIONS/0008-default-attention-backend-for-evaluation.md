# 0008: Keep the default attention backend for evaluation until quality is compared

Status: accepted. Date: 2026-11-26.

## Context

On vLLM 0.33.0 ROCm, Qwen3.8-27B decodes with the `ROCM_ATTN` Triton fallback, which slows down with context
(69 tok/s at 0.8k tokens, 7.6 tok/s at 61k). `ROCM_AITER_UNIFIED_ATTN` is 1.1 to 6 times faster on the same GPU
([COMPATIBILITY.md](../COMPATIBILITY.md#serving-attention-backend-and-long-context-decode-vllm-0330-rocm-qwen38-27b)).
Greedy outputs differ between the two after a few hundred characters.

## Decision

All benchmark and baseline runs keep the default backend, so they stay comparable with the smoke runs of
2026-11-25. Switching is a separate, paired experiment on devbench (same tasks, harnesses and sampling, only the
backend changes). If success rates do not differ beyond noise, rollouts for training use the faster backend and
the serving configs are updated with a dated note.

## Consequences

Evaluation stays slow for long contexts until the comparison is done; the comparison costs one devbench run per
harness.
