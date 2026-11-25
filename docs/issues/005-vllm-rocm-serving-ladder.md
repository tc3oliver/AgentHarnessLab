# 005: Serve the base model with vLLM on ROCm and pass ladder rungs 0-3

Milestone: **v0.1**
Depends on: [002](002-pin-and-lock-environment.md)

## Context

Nothing has run on a GPU. See ../HARDWARE.md for rungs and risks.

## Scope

Bring up vLLM for Qwen3.8-27B on 1 GPU with the prefix-cache flag, verify device mapping, then run rungs 0-3. Record fallbacks tried. Replace estimates in HARDWARE.md with measurements.

## Acceptance criteria

- Rungs 0-3 pass with the stated criteria, or each failure is documented with the fallback tried.
- Device mapping HIP to physical recorded.
- Measured memory and throughput added to the hardware doc.

## Test method

Run the ladder scripts; keep logs with the manifest.
