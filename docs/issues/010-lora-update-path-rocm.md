# 010: LoRA update path on ROCm

Milestone: **v0.2**
Depends on: [005](005-vllm-rocm-serving-ladder.md)

## Context

Adapter reaches the server by disk plus `/v1/load_lora_adapter`; needs `--enable-lora`, runtime updating env flag, `--max-loras >= max_staleness + 2` (../UPSTREAM.md, Constraint 5).

## Scope

Verify the round trip on ROCm: save, load, serve, hash check, repeated updates, staleness behaviour.

## Acceptance criteria

- Served outputs change after an update and the served adapter hash matches.
- 100 consecutive updates without a leak or hang.
- Failure modes documented.

## Test method

Ladder rungs 5 and 7.
